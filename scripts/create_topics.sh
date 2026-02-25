docker compose exec redpanda rpk topic create farmer-messages-text --partitions 6 --replicas 1
docker compose exec redpanda rpk topic create farmer-messages-image --partitions 3 --replicas 1
docker compose exec redpanda rpk topic create farmer-messages-voice --partitions 3 --replicas 1
docker compose exec redpanda rpk topic list