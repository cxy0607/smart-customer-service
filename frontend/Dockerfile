# 前端镜像：多阶段构建（面试可讲）
# 阶段 1（build）：Node 环境编译出静态文件，最终镜像不携带 Node 运行时
# 阶段 2（serve）：nginx 托管静态文件 + 反向代理 /api 到后端
# 好处：最终镜像只有几 MB（nginx:alpine），无 Node 环境，攻击面小
FROM node:22-alpine AS build

WORKDIR /app

# 国内环境使用 npmmirror 加速
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com \
    && npm install

COPY . .
RUN npm run build

FROM nginx:alpine

# 编译产物拷贝到 nginx 静态目录
COPY --from=build /app/dist /usr/share/nginx/html
# 自定义 nginx 配置：history 路由 + /api 反向代理 + SSE 流式支持
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
