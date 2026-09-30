# Placeraa local Docker environment

A local development/demo stack. Compose project name: `placeraa`.

| Service   | Image (pinned by digest) | Notes                                      |
|-----------|--------------------------|--------------------------------------------|
| `mariadb` | `mariadb:10.8`           | data in volume `placeraa_mariadb-data`     |
| `redis`   | `redis:alpine`           | cache, queue and socketio, no persistence  |
| `frappe`  | `frappe/bench`           | web on `8000`, socketio on `9000`          |

## How the source is wired

```
this repository ─────────────► /home/frappe/frappe-bench/apps/lms   (bind mount)
placeraa/       ─────────────► /home/frappe/frappe-bench/apps/placeraa (bind mount, the Placeraa app)
docker/         ─────────────► /workspace                            (init.sh, Procfile)
volume bench-data ───────────► /home/frappe/frappe-bench             (env, sites, apps/frappe, apps/payments)
volume lms-node-modules ─────► .../apps/lms/frontend/node_modules
volume mariadb-data ─────────► /var/lib/mysql
```

The container runs the LMS source checked out in this repository. It never
clones LMS from GitHub. `init.sh` refuses to start if `apps/lms` is not a bind
mount, so it cannot silently fall back to another copy.

The Placeraa Frappe app lives in `placeraa/` in this repository and is mounted
as its own app, next to `lms`. Placeraa code goes there, never into `lms/`.
It was created once with `bench new-app placeraa --no-git` and installed with
`bench --site lms.localhost install-app placeraa`; both results (the
`apps.txt` entry, the editable install and the site registration) live in the
`bench-data` volume and the database. Changing the mounts needs the service to
be recreated (`docker compose ... up -d frappe`), not just restarted.

The bench, the site and the database are in named volumes, so
`docker compose down` and container recreation do not lose the site.

The web server is started by the committed `docker/Procfile`
(`bench start --procfile /workspace/Procfile`), bound to `0.0.0.0:8000`.
Nothing inside a container needs to be edited by hand.

## Setup

```bash
cp docker/.env.example docker/.env
```

`MYSQL_ROOT_PASSWORD` in `docker/.env` must match the root password already
stored in the seeded database (the development default is `123`).

### Seeding the volumes from an existing bench

`init.sh` does not create a bench or a site. The `bench-data` and
`mariadb-data` volumes must be seeded once from a backup of a working install
(a tar of `/home/frappe/frappe-bench` and a tarball of the MariaDB data
directory). Run these from the repository root, with the stack created but not
started:

```bash
export MSYS_NO_PATHCONV=1   # Git Bash on Windows only
BACKUP="<directory containing frappe-bench.tar and mariadb-data.tgz>"
BENCH_IMAGE=frappe/bench@sha256:a99c611f8f89bd04437b3cbd4ed0b11db8a0aa5b60fade4f29d02090f330e4af
DB_IMAGE=mariadb@sha256:456709ab146585d6189da05669b84384518baecd83670c9e5221f8c20a47cf1e

docker compose -f docker/docker-compose.yml up --no-start     # creates the volumes only

# MariaDB data directory
docker run --rm --entrypoint tar -v placeraa_mariadb-data:/to -v "$BACKUP":/b:ro \
  $DB_IMAGE -xzf /b/mariadb-data.tgz -C /to --same-owner

# Bench (without the stray nested frappe-bench/frappe-bench directory)
docker run --rm --user root --entrypoint tar \
  -v placeraa_bench-data:/home/frappe/frappe-bench -v "$BACKUP":/b:ro \
  $BENCH_IMAGE -xf /b/frappe-bench.tar -C /home/frappe --same-owner \
  --exclude='frappe-bench/frappe-bench'

# frontend node_modules, taken from the restored bench
docker run --rm --user root --entrypoint bash \
  -v placeraa_bench-data:/src:ro -v placeraa_lms-node-modules:/dst \
  $BENCH_IMAGE -c 'cp -a /src/apps/lms/frontend/node_modules/. /dst/'
```

Only seed volumes that are empty. Extracting over a live bench or database
overwrites it.

## Everyday use

```bash
docker compose -f docker/docker-compose.yml up -d        # start
docker compose -f docker/docker-compose.yml logs -f frappe
docker compose -f docker/docker-compose.yml stop         # stop, keeps everything
docker compose -f docker/docker-compose.yml exec frappe bench --site lms.localhost migrate
docker compose -f docker/docker-compose.yml exec frappe bash
```

Open <http://localhost:8000> (the SPA is at `/lms`).

If `lms/www/_lms.html` or `lms/public/frontend/` is missing (both are
gitignored build output), `init.sh` builds the frontend on start. To rebuild
it later:

```bash
docker compose -f docker/docker-compose.yml exec frappe bash -c 'cd apps/lms/frontend && yarn build'
```

Set `RUN_MIGRATE=1` in `docker/.env` to run `bench migrate` once at start.

## Never run these

Because this repository is bind-mounted into the bench, some `bench` commands
act on your working tree, and some destroy data.

| Command | Why |
|---|---|
| `docker compose down -v`, `docker volume rm`, `docker volume prune`, `docker system prune --volumes` | delete the database and/or the bench |
| `bench new-site --force`, `bench drop-site`, `bench reinstall`, `bench restore` | wipe or overwrite the site database |
| `bench uninstall-app lms`, `bench remove-app lms` | remove data, or recursively delete `apps/lms`, which is this repository |
| `bench init` inside `/home/frappe/frappe-bench` | its failure cleanup deletes the bench directory, including the mounted repository |
| `bench update`, `bench get-app lms` | pull or reset the app, or replace it from GitHub |
| `git reset --hard`, `git clean -fdx` | discard work in the repository |

`docker compose down` (without `-v`) is safe: volumes are kept.

## Rolling back to the previous environment

The earlier `lms` project (`lms-*` containers, volume `lms_mariadb-data`) is
left untouched. Stop this stack first (ports 8000 and 9000 collide), then
restore the old start script, which the old container mounts from this
directory, and start the old containers:

```bash
docker compose -f docker/docker-compose.yml stop
git show upstream-base-086c813c:docker/init.sh > docker/init.sh    # temporary, do not commit
docker start lms-mariadb-1 lms-redis-1 lms-frappe-1
```
