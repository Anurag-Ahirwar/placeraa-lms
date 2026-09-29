#!/usr/bin/env bash
# Start the Placeraa development bench.
#
# Runs on every container start and is idempotent. It never creates a bench,
# a site or an app: no `bench init`, `bench get-app` or `bench new-site`.
# It only checks that the persistent bench and the mounted source are in place,
# then hands over to `bench start`.
set -euo pipefail

BENCH_DIR=/home/frappe/frappe-bench
SITE="${SITE_NAME:-lms.localhost}"

fail() {
	echo "init.sh: $*" >&2
	exit 1
}

# The container's home is not persistent and the bind mount is owned by another
# user, so git would refuse the repository ("dubious ownership").
git config --global --add safe.directory '*'

[ -x "$BENCH_DIR/env/bin/python" ] && [ -d "$BENCH_DIR/apps/frappe" ] ||
	fail "no bench in $BENCH_DIR. The bench-data volume has not been seeded (see docker/README.md)."
[ -f "$BENCH_DIR/sites/$SITE/site_config.json" ] ||
	fail "site $SITE not found in the bench-data volume. Refusing to create or overwrite it."

cd "$BENCH_DIR"

# apps/lms must be the bind-mounted local repository. Refusing otherwise means
# this can never silently run the GitHub clone hidden underneath the mount.
awk -v p="$BENCH_DIR/apps/lms" '$5 == p { found = 1 } END { exit !found }' /proc/self/mountinfo ||
	fail "$BENCH_DIR/apps/lms is not a bind mount of the local repository."
[ -f apps/lms/lms/hooks.py ] || fail "apps/lms is mounted but does not contain the LMS source."

grep -qx lms sites/apps.txt || fail "lms is missing from sites/apps.txt."
env/bin/python -c "import lms" || fail "the lms app is not importable from the bench environment."

# The SPA build output is gitignored, so a clean checkout has none of it.
if [ ! -f apps/lms/lms/www/_lms.html ] || [ ! -d apps/lms/lms/public/frontend ]; then
	echo "init.sh: building the LMS frontend (missing from the source tree)..."
	(cd apps/lms/frontend && yarn install --frozen-lockfile && yarn build)
fi

if [ "${RUN_MIGRATE:-0}" = "1" ]; then
	echo "init.sh: RUN_MIGRATE=1, migrating $SITE"
	bench --site "$SITE" migrate
fi

exec bench start --procfile /workspace/Procfile
