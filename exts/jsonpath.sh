#!/bin/sh

# shellcheck shell=bash

set -eo pipefail

suffix="${suffix-""}"

EXT=jsonpath
EXT_DIR="${EXT}"
CONFIGURE_ARGS=""
URL=https://pecl.php.net/get/jsonpath-1.0.0.tgz

printf "\033[44;37m Start build extension %s \033[0m\n" "${EXT}"

mkdir -p "/usr/src/$EXT"
cd /usr/src

curl -sfSL -o ext.tar.gz "$URL"
tar -xf ext.tar.gz -C "${EXT}" --strip-components=1
rm ext.tar.gz

cd "${EXT}"
    printf "\033[44;37m PHPIZE and configure %s \033[0m\n" "${EXT}"
    "phpize${suffix}"
    ./configure \
        "--with-php-config=/usr/bin/php-config${suffix}" \
        $CONFIGURE_ARGS

    # copy before-build source for debug use
    mkdir -p /tmp/withdebug/usr/src
    cp -r /usr/src/"${EXT}" /tmp/withdebug/usr/src/"${EXT}"

    # start build
    printf "\033[44;37m make %s \033[0m\n" "${EXT}"
    make -j "$(nproc)" EXTRA_CFLAGS='-g -O2'

    # install for stripped and withdebug
    printf "\033[44;37m install %s \033[0m\n" "${EXT}"
    for d in /tmp/stripped /tmp/withdebug
    do
        make install INSTALL_ROOT="$d"
        mkdir -p "$d/etc/php${suffix}/conf.d"
        echo "extension=$EXT" > "$d/etc/php${suffix}/conf.d/50_${EXT}.ini"
    done

    # strip only in the stripped dir
    cd /tmp/stripped
        find . -type f -name "*.so" -exec strip -s {} \; || :
    
# show result
printf "\033[42;37m Built %s is \033[0m\n" "${EXT}"
php -dextension=/usr/src/${EXT_DIR}/.libs/${EXT}.so --ri ${EXT}
