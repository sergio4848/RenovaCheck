# syntax=docker/dockerfile:1.7
# One image for the web app (Apache + mod_php), the queue worker and one-off artisan commands.
# pcntl lets the queue worker enforce job timeouts.
#
#   docker build --build-context certs=../../infra/certs -t renova-web .
#   docker build --build-context certs=../../infra/certs --build-arg INSTALL_DEV=false -t renova-web:prod .

ARG PHP_VERSION=8.3.26

FROM composer:2.8.12 AS composer

FROM php:${PHP_VERSION}-apache-bookworm AS runtime
ARG INSTALL_DEV=true

# Optional extra CA certificates for builds behind a TLS-intercepting proxy (see infra/certs/README.md).
COPY --from=certs . /usr/local/share/ca-certificates/extra/
RUN update-ca-certificates >/dev/null 2>&1 || true

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev libicu-dev libzip-dev unzip git \
    && docker-php-ext-install -j"$(nproc)" pdo_pgsql intl zip opcache bcmath pcntl \
    && rm -rf /var/lib/apt/lists/*

RUN a2enmod rewrite headers >/dev/null
COPY docker/apache.conf /etc/apache2/sites-available/000-default.conf
COPY docker/php.ini "$PHP_INI_DIR/conf.d/zz-renova.ini"
RUN sed -ri 's/^ServerTokens .*/ServerTokens Prod/; s/^ServerSignature .*/ServerSignature Off/' /etc/apache2/conf-available/security.conf

COPY --from=composer /usr/bin/composer /usr/bin/composer
WORKDIR /var/www/html

# Dependency layer (cached until composer.json/lock change). The optional `vendor-seed` build
# context pre-populates vendor/ for hosts that cannot download package archives; composer
# install then only verifies it against composer.lock.
COPY composer.json composer.lock ./
COPY --from=vendor-seed . ./vendor/
RUN rm -f vendor/README.md
# git is the fallback when a package's dist archive cannot be downloaded.
RUN --mount=type=cache,target=/root/.cache/composer \
    COMPOSER_ALLOW_SUPERUSER=1 composer install --no-interaction --no-scripts --no-autoloader --prefer-dist \
        $( [ "$INSTALL_DEV" = "true" ] || echo "--no-dev" )

COPY . .
RUN COMPOSER_ALLOW_SUPERUSER=1 composer dump-autoload --optimize --no-interaction \
    && php artisan package:discover --ansi \
    && touch .env \
    && mkdir -p storage/framework/cache storage/framework/sessions storage/framework/views storage/logs \
    && chown -R www-data:www-data storage bootstrap/cache

EXPOSE 80
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=15s \
    CMD curl -fsS http://127.0.0.1/up >/dev/null || exit 1
CMD ["apache2-foreground"]
