# TableTop
codebase for Tabletop project

### startDB
docker run --name tabletop-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=tabletop_db \
  -p 5432:5432 \
  -d postgres