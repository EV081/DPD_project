#!/bin/sh
# Entrypoint del contenedor week10.
#   docker compose run pipeline full|demand|live|loop|export|check|pytest ...
set -e

cmd="${1:-full}"

case "$cmd" in
  pytest|test)
    shift
    exec pytest -q -p no:cacheprovider tests "$@"
    ;;
  sh|shell)
    shift
    exec /bin/sh "$@"
    ;;
esac

exec python -m pipeline.run "$@"
