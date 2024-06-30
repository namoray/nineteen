pm2 delete peer_at_sql_db
pm2 start --name "peer_at_sql_db" "sqlite_web vision_database.db -H 0.0.0.0 -p 9991"