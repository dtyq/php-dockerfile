# Copyright 2025 DTYQ <dev@dtyq.com>
# Copyright 2025 Yun Dou <douyun@dtyq.com>

ARG ALPINE_VERSION

FROM alpine:$ALPINE_VERSION as php_base

ARG ALPINE_VERSION
ARG PHP_VERSION
ARG EXT_DEV
ARG MIRROR
ARG CURL_PROXY

RUN set -eo pipefail ; \
    cp /etc/apk/repositories /etc/apk/repositories.orig && \
    sed -i "s|https://dl-cdn.alpinelinux.org|${MIRROR}|g" /etc/apk/repositories && \
    # setup suffix
    case "${PHP_VERSION}-${ALPINE_VERSION}" in \
        "8.4-edge"|"8.4-3.21") suffix=84;; \
        "8.3-edge"|"8.3-3.21"|"8.3-3.20"|"8.3-3.19") suffix=83;; \
        "8.2-edge"|"8.2-3.21"|"8.2-3.20"|"8.2-3.19"|"8.2-3.18") suffix=82;; \
        "8.1-edge"|"8.1-3.18"|"8.1-3.17"|"8.1-3.16") suffix=81;; \
        "8.0-3.16"|"8.0-3.15") suffix=8;; \
        "7.4-3.15") suffix=7;; \
        *) echo "not supported php ${PHP_VERSION} on alpine ${ALPINE_VERSION}"; exit 1;; \
    esac ; \
    DEPS="$(echo "${EXT_DEV}" | sed 's/-dev//g')" ; \
    apk add --no-cache \
        # Install base packages ('ca-certificates' will install 'nghttp2-libs')
        ca-certificates \
        curl \
        wget \
        tar \
        xz \
        tzdata \
        pcre \
        $DEPS \
        php${suffix}~${PHP_VERSION} \
        # align phpx-common with phpx version
        php${suffix}-common~${PHP_VERSION} \
        php${suffix}-bcmath~${PHP_VERSION} \
        php${suffix}-curl~${PHP_VERSION} \
        php${suffix}-tokenizer~${PHP_VERSION} \
        php${suffix}-ctype~${PHP_VERSION} \
        php${suffix}-dom~${PHP_VERSION} \
        php${suffix}-gd~${PHP_VERSION} \
        php${suffix}-fileinfo~${PHP_VERSION} \
        php${suffix}-intl~${PHP_VERSION} \
        php${suffix}-iconv~${PHP_VERSION} \
        php${suffix}-mbstring~${PHP_VERSION} \
        php${suffix}-mysqlnd~${PHP_VERSION} \
        php${suffix}-openssl~${PHP_VERSION} \
        php${suffix}-pdo~${PHP_VERSION} \
        php${suffix}-pdo_mysql~${PHP_VERSION} \
        php${suffix}-pdo_sqlite~${PHP_VERSION} \
        php${suffix}-pdo_pgsql~${PHP_VERSION} \
        php${suffix}-phar~${PHP_VERSION} \
        php${suffix}-posix~${PHP_VERSION} \
        php${suffix}-sockets~${PHP_VERSION} \
        php${suffix}-sodium~${PHP_VERSION} \
        php${suffix}-sysvshm~${PHP_VERSION} \
        php${suffix}-sysvmsg~${PHP_VERSION} \
        php${suffix}-sysvsem~${PHP_VERSION} \
        php${suffix}-zip~${PHP_VERSION} \
        php${suffix}-xml~${PHP_VERSION} \
        php${suffix}-xmlreader~${PHP_VERSION} \
        php${suffix}-xmlwriter~${PHP_VERSION} \
        php${suffix}-simplexml~${PHP_VERSION} \
        php${suffix}-pcntl~${PHP_VERSION} \
        php${suffix}-opcache~${PHP_VERSION} \
        php${suffix}-pecl-redis \
        php${suffix}-pecl-igbinary \
        php${suffix}-pecl-mongodb \
        php${suffix}-pecl-yaml \
        php${suffix}-pecl-zstd \
    && \
    ln -sf /usr/bin/php${suffix} /usr/bin/php && \
    rm -rf /var/cache/apk/* /tmp/* && \
    # install composer
    https_proxy="${CURL_PROXY}" curl -sfSL -o /usr/local/bin/composer https://getcomposer.org/download/latest-stable/composer.phar && \
    chmod 0755 /usr/local/bin/composer && \
    mkdir ~/.composer && \
    # recover mirror
    mv /etc/apk/repositories.orig /etc/apk/repositories && \
    # validate extensions loading
    { [ x$(php -r '' 2>&1) = "x" ] || exit 1; } && \
    printf "\033[42;37m PHP version is \033[0m\n" && \
    php -v && \
    printf "\033[42;37m PHP modules are \033[0m\n" && \
    php -m && \
    printf "\033[42;37m Build Completed :).\033[0m\n"
    

FROM php_base as ext_builder

ARG ALPINE_VERSION
ARG PHP_VERSION
ARG MIRROR
ARG EXT_URL
ARG EXT_DEV
ARG CURL_PROXY

# build extension
RUN set -eo pipefail; \
    cp /etc/apk/repositories /etc/apk/repositories.orig && \
    sed -i "s|https://dl-cdn.alpinelinux.org|${MIRROR}|g" /etc/apk/repositories && \
    # setup suffix
    case "${PHP_VERSION}-${ALPINE_VERSION}" in \
        "8.4-edge"|"8.4-3.21") suffix=84;; \
        "8.3-edge"|"8.3-3.21"|"8.3-3.20"|"8.3-3.19") suffix=83;; \
        "8.2-edge"|"8.2-3.21"|"8.2-3.20"|"8.2-3.19"|"8.2-3.18") suffix=82;; \
        "8.1-edge"|"8.1-3.18"|"8.1-3.17"|"8.1-3.16") suffix=81;; \
        "8.0-3.16"|"8.0-3.15") suffix=8;; \
        "7.4-3.15") suffix=7;; \
        *) echo "not supported php ${PHP_VERSION} on alpine ${ALPINE_VERSION}"; exit 1;; \
    esac ; \
    # build time dependencies
    apk add --no-cache --virtual .build-deps \
        # build tools
        autoconf \
        automake \
        file \
        gcc \
        g++ \
        libc-dev \
        make \
        pkgconf \
        re2c \
        libtool \
        # headers
        php${suffix}-dev~${PHP_VERSION} \
        php${suffix}-pear~${PHP_VERSION} \
        zlib-dev \
        ${EXT_DEV} \
    && \
    # download sw* source
    mkdir -p /usr/src && \
    cd /usr/src && \
    https_proxy="${CURL_PROXY}" curl -sfSL $EXT_URL -o ext.tar.gz && \
    { \
        tar tf ext.tar.gz | grep swoole-src && export EXT=swoole EXT_DIR=swoole || export EXT=swow EXT_DIR=swow/ext ; \
    } && \
    mkdir -p /usr/src/"${EXT}" && \
    tar -xf ext.tar.gz -C "${EXT}" --strip-components=1 && \
    rm ext.tar.gz && \
    # build sw*
    cd "${EXT}" && \
    if [ "${EXT}" = "swow" ]; \
    then \
        cd ext && \
        phpize${suffix} && \
        ./configure \
            --with-php-config=/usr/bin/php-config${suffix} \
            --enable-swow-curl \
            --enable-swow-ssl && \
        echo "extension=${EXT}.so" > /tmp/50_${EXT}.ini ; \
    else \
        phpize${suffix} && \
        ./configure \
            --with-php-config=/usr/bin/php-config${suffix} \
            --enable-openssl \
            --enable-swoole-curl \
            --enable-cares \
            --enable-swoole-pgsql && \
        echo "extension=${EXT}.so" > /tmp/50_${EXT}.ini && \
        echo "swoole.use_shortname = 'Off'" >> /tmp/50_${EXT}.ini ; \
    fi &&\
    # copy before-build source for debug use
    mkdir -p /tmp/withdebug/usr/src && \
    cp -r /usr/src/"${EXT}" /tmp/withdebug/usr/src/"${EXT}" && \
    # start build
    make -s -j$(nproc) EXTRA_CFLAGS='-g -O2' && \
    # install for stripped and withdebug
    for d in /tmp/stripped /tmp/withdebug ; \
    do \
        make install INSTALL_ROOT="$d" && \
        mkdir -p "$d"/etc/php${suffix}/conf.d && \
        cp /tmp/50_${EXT}.ini "$d"/etc/php${suffix}/conf.d/50_${EXT}.ini && \
        echo "memory_limit=1G" > "$d"/etc/php${suffix}/conf.d/00_memory_limit.ini && \
        echo "zend_extension=opcache" > "$d"/etc/php${suffix}/conf.d/00_opcache.ini && \
        echo "opcache.enable_cli = 'On'" >> "$d"/etc/php${suffix}/conf.d/00_opcache.ini ; \
    done && \
    # if swoole 4.8, build pgsql binding
    if [ "${EXT}" = "swoole" ] ; \
    then \
        cd /usr/src/swoole && \
        if [ ! -f ext-src/swoole_pgsql.cc ] && \
            [ ! -f ext-src/swoole_pgsql_coro.cc ] && \
            [ ! -f ext-src/swoole_postgresql_coro.cc ] ; \
        then \
            # install into buildroot for pgsql to use
            make install && \
            https_proxy="${CURL_PROXY}" curl -sfSL \
                https://github.com/dixyes/ext-postgresql/archive/refs/heads/4.8.x.tar.gz \
                -o /usr/src/ext-postgresql.tar.gz && \
            mkdir /usr/src/ext-postgresql && \
            tar -xf /usr/src/ext-postgresql.tar.gz --strip-components=1 -C /usr/src/ext-postgresql && \
            rm /usr/src/ext-postgresql.tar.gz && \
            cd /usr/src/ext-postgresql && \
            phpize${suffix} && \
            # configure
            ./configure \
                --with-php-config=/usr/bin/php-config${suffix} \
            && \
            # copy before-build source for debug use
            cp -r /usr/src/ext-postgresql /tmp/withdebug/usr/src/ext-postgresql && \
            # start build
            make -s -j$(nproc) EXTRA_CFLAGS='-g -O2' && \
            # install for stripped and withdebug
            for d in /tmp/stripped /tmp/withdebug ; \
            do \
                make install INSTALL_ROOT="$d" && \
                mkdir -p "$d"/etc/php${suffix}/conf.d && \
                echo "extension=swoole_postgresql.so" >> "$d"/etc/php${suffix}/conf.d/50_${EXT}.ini ; \
            done || exit 1 ; \
        fi ; \
    fi ; \
    # strip only in the stripped dir
    cd /tmp/stripped && \
    { find . -type f -name "*.so" -exec strip -s {} \; || : ; } &&\
    # recover mirror
    mv /etc/apk/repositories.orig /etc/apk/repositories && \
    # show result
    printf "\033[42;37m Built ${EXT} is \033[0m\n" && \
    php -dextension=/usr/src/${EXT_DIR}/.libs/${EXT}.so --ri ${EXT}

FROM ext_builder as exts_builder

ARG ALPINE_VERSION
ARG PHP_VERSION
ARG EXTS

COPY exts /usr/src/exts/

RUN set -eo pipefail && \
    # setup suffix
    case "${PHP_VERSION}-${ALPINE_VERSION}" in \
        "8.4-edge"|"8.4-3.21") suffix=84;; \
        "8.3-edge"|"8.3-3.21"|"8.3-3.20"|"8.3-3.19") suffix=83;; \
        "8.2-edge"|"8.2-3.21"|"8.2-3.20"|"8.2-3.19"|"8.2-3.18") suffix=82;; \
        "8.1-edge"|"8.1-3.18"|"8.1-3.17"|"8.1-3.16") suffix=81;; \
        "8.0-3.16"|"8.0-3.15") suffix=8;; \
        "7.4-3.15") suffix=7;; \
        *) echo "not supported php ${PHP_VERSION} on alpine ${ALPINE_VERSION}"; exit 1;; \
    esac ; \
    export suffix ; \
    _IFS="$IFS" ; \
    IFS="-" ; \
    for ext in $EXTS ; \
    do \
        [ "x${ext}" = "x" ] && continue ; \
        IFS="$_IFS" "/usr/src/exts/${ext}.sh" ; \
    done

FROM php_base as stripped

COPY --from=exts_builder /tmp/stripped /

FROM php_base as debuggable

COPY --from=exts_builder /tmp/withdebug /
