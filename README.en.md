# php-dockerfile

Simple build scripts/Dockerfile for php base images

## Usage

The alpine branch is for building images based on alpine.

### Tag naming convention

```plain
<php version, must be major.minor>-alpine-<alpine version, must be major.minor>-swoole-<swoole version, must be major.minor.revision>[-extensions,-extensions]
```

Extension names must be sorted alphabetically (to ensure uniqueness)

For example:

```plain
8.1-alpine-3.16-swoole-5.0.2-jsonpath-xlswriter
```

### debuggable tag

The tag can be appended with `-debuggable`

The debuggable version of the image contains source code and debug symbols, for debugging purposes.

### Build

```bash
IMAGE_NAME=some-registry.domain/some-namespace/some-image-name ./build.py "<tag>"
```

Where `IMAGE_NAME` is the image name, for example `ghcr.io/myorg/php-dockerfile`

You can also set the following environment variables

```text
TRY_MIRRORS

If you are building inside a cloud service provider's intranet, you can set this variable to the intranet mirror, separated by commas. The default is the intranet mirrors of Aliyun and Tencent Cloud.

PUBLIC_MIRROR

The default image source
```

## Tasks

Some TODOs that have not been done yet, PRs are welcome.

- [ ] Refactor build.py to use argparse for command line parameters
- [ ] Update exts
- [ ] Add more PHP extensions
- [ ] Update PHP-alpine version mapping (needs to be updated continuously, can be done with a GitHub workflow)

## Open source license

```text
Copyright 2025 DTYQ <dev@dtyq.com>
Copyright 2025a Yun Dou <douyun@dtyq.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```
