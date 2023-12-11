# # Create a Kafka topic named "nii_case"
# docker exec -it <container_id> /bin/bash 
# kafka-topics --create --topic nii_case --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# kafka-topics --list --bootstrap-server localhost:9092