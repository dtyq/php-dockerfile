# php-dockerfile

简单的带一些扩展的php基础镜像构建脚本/Dockerfile

## 用法

alpine分支用于构建基于alpine的镜像

### tag命名约定

```plain
<php版本号，必须是主版本号.小版本号>-alpine-<alpine版本号，必须是主版本号.子版本号>-swoole-<swoole版本号，必须是主版本号.子版本号.修订版本号>[-扩展们,-扩展们]
```

扩展名必须按字母表排序（为了保证唯一性）

例如

```plain
8.1-alpine-3.16-swoole-5.0.2-jsonpath-xlswriter
```

### debuggable tag

普通tag后可以加`-debuggable`

这个版本的镜像是带源码和调试符号的，可以调试

### 构建

```bash
IMAGE_NAME=some-registry.domain/some-namespace/some-image-name ./build.py "<tag>"
```

其中`IMAGE_NAME`为镜像名，比如`ghcr.io/mycomp/php-dockerfile`

也可以配置以下环境变量

```text
TRY_MIRRORS

如果在云服务器提供商内网构建，可以将这个变量设置为内网镜像，逗号分隔。默认是阿里云和腾讯云的内网镜像

PUBLIC_MIRROR

默认使用的镜像源
```

## Tasks

一些TODO但一直没做的活，欢迎PR

- [ ] build.py整理下，用argparse处理命令行参数
- [ ] 更新exts
- [ ] 添加更多PHP扩展
- [ ] 更新PHP-alpine版本对应（需要持续更新，可以做个GitHub workflow）

## 开源许可

```text
Copyright 2025 DTYQ <dev@dtyq.com>
Copyright 2025 Yun Dou <douyun@dtyq.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
