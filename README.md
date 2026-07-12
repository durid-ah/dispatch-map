# Local development DB

These are notes for setting up a db for local development. For prod obviously replace the password with a more secure password and config.

`postgresql://dispatch:dispatch@localhost:5432/dispatch_map`

```bash
docker build -t dispatch-map-postgres docker/postgres

docker run -d \
  --name dispatch-map-db \
  -p 5432:5432 \
  -v dispatch_map_pgdata:/var/lib/postgresql/data \
  dispatch-map-postgres
```
