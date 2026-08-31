#!/usr/bin/env node
/**
 * commit-gate.js — git commit 提交门禁（Claude Code PreToolUse hook）
 *
 * 作用：拦截 git commit 命令，提交前自动跑「后端 pytest + 前端 vitest 测试 + 前端构建」。
 *       全过 → 放行；有失败 → 拦截并输出中文友好提示。
 *
 * 退出码约定：
 *   0 = 放行（非 commit 命令 / --no-verify 逃生门 / 检查全通过 / 内部异常一律放行）
 *   2 = 拦截（检查不通过），stderr 输出中文提示给 Claude 转达用户
 *
 * 设计原则：宁可漏拦，不可误拦（fail-open）。脚本自身出任何问题都放行，
 *           不阻塞用户提交，只对"明确知道在提交且检查失败"的情况拦截。
 *
 * 测试开关：环境变量 COMMIT_GATE_FORCE_FAIL=1 可强制返回拦截（验证拦截功能用）
 */
'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// 脚本位于 .claude/hooks/ 下，向上两级即项目根（不依赖 cwd，最稳）
const PROJECT_ROOT = path.resolve(__dirname, '..', '..');
const IS_WIN = process.platform === 'win32';
// Windows 下 npm 必须用 .cmd，否则 ENOENT
const NPM = IS_WIN ? 'npm.cmd' : 'npm';
// 后端虚拟环境里的 Python（Windows 路径分隔符在 cmd shell 下正斜杠同样可用）
const PYTHON = path.join(PROJECT_ROOT, 'backend', '.venv', 'Scripts', 'python.exe');

// ── 1. 读 hook 输入（任何异常返回 null → 放行） ──
function readHookInput() {
  try {
    const raw = fs.readFileSync(0, 'utf8');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

// ── 2. 判断是不是 git commit 命令 ──
// 按 && ; || 切分命令链，逐段判断：段首必须是 git，
// 之后允许 git 全局选项（-C <dir>、-c k=v、--git-dir <dir>），遇到 commit 即命中；
// 遇到非选项 token（log/status 等）即否定。echo "git commit" 不会误伤。
function isGitCommit(cmd) {
  if (typeof cmd !== 'string') return false;
  return cmd.split(/\s*(?:&&|;|\|\|)\s*/).some((seg) => {
    const tokens = seg.trim().split(/\s+/).filter(Boolean);
    if (tokens[0] !== 'git') return false;
    for (let i = 1; i < tokens.length; i++) {
      const t = tokens[i];
      if (t === 'commit') return true; // 覆盖 -m/-am/--amend/-F 等变体
      if (t.startsWith('-') && t.length > 1) {
        // git 全局选项后面跟一个参数值，跳过去
        if (/^(-C|-c|--git-dir|--work-tree|--namespace|--exec-path)$/.test(t)) i += 1;
        continue;
      }
      return false; // 遇到非选项 token（如 log/status），不是 commit
    }
    return false;
  });
}

// ── 3. 快速检查执行器 ──
// Windows 下直接 spawn .cmd 文件会报 EINVAL，必须走 shell（cmd.exe）。
// 命令字符串全部由本文件硬编码，不含任何用户输入，无注入风险。
function runCheck(commandLine, timeoutMs, cwd) {
  const r = spawnSync(commandLine, {
    cwd,
    encoding: 'utf8',
    timeout: timeoutMs,
    maxBuffer: 10 * 1024 * 1024,
    windowsHide: true,
    shell: true
  });
  if (r.error) return { ok: false, detail: `命令无法运行：${r.error.message}` };
  return { ok: r.status === 0, detail: (r.stdout || '') + (r.stderr || '') };
}

function truncate(text, maxLines) {
  return String(text).split(/\r?\n/).slice(0, maxLines).join('\n');
}

function main() {
  const input = readHookInput();
  if (!input || !input.tool_input) return 0; // 解析失败 → 放行

  const command = input.tool_input.command;
  if (!isGitCommit(command)) return 0; // 绝大多数调用走这里，必须快

  // 逃生门：--no-verify 跳过检查
  if (command.includes('--no-verify')) {
    process.stderr.write('ℹ️ 检测到 --no-verify，已跳过提交门禁（请确认是故意跳过）。\n');
    return 0;
  }

  // 验证用测试开关
  if (process.env.COMMIT_GATE_FORCE_FAIL === '1') {
    process.stderr.write(
      '❌ 提交被拦下：门禁处于测试模式（COMMIT_GATE_FORCE_FAIL=1），此提示用于验证拦截功能。\n'
    );
    return 2;
  }

  const checks = [
    {
      label: '后端测试（pytest）',
      run: () =>
        runCheck(
          `"${PYTHON}" -m pytest tests/ -q`,
          180_000, // 测试含真实百炼 API 调用，放宽超时
          path.join(PROJECT_ROOT, 'backend')
        )
    },
    {
      label: '前端测试（vitest）',
      run: () =>
        runCheck(
          `${NPM} run test`,
          180_000, // jsdom 环境初始化较慢，实测约 1 分钟
          path.join(PROJECT_ROOT, 'frontend')
        )
    },
    {
      label: '前端构建（npm run build）',
      run: () =>
        runCheck(
          `${NPM} run build`,
          120_000,
          path.join(PROJECT_ROOT, 'frontend')
        )
    }
  ];

  const failures = [];
  const started = Date.now();
  for (const check of checks) {
    const result = check.run();
    if (!result.ok) failures.push({ label: check.label, detail: truncate(result.detail, 12) });
  }
  const seconds = ((Date.now() - started) / 1000).toFixed(1);

  if (failures.length === 0) {
    process.stderr.write(`✅ 提交门禁检查通过（${seconds} 秒），放行提交。\n`);
    return 0;
  }

  let msg = `❌ 提交被拦下了：快速质量检查没通过（${seconds} 秒）\n`;
  for (const f of failures) {
    msg += `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n✗ ${f.label} —— 失败\n${f.detail.trim()}\n`;
  }
  msg += '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n';
  msg += '建议：先让 tester1 / quality-engineer 修复上面的问题，再重新提交。\n';
  msg += '紧急情况逃生门（不推荐）：git commit --no-verify -m "..." 可跳过检查。\n';
  process.stderr.write(msg);
  return 2;
}

process.exit(main());
