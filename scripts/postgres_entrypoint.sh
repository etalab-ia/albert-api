#!/bin/bash

function create_database() {
	local database=$1
	echo "  Creating database '$database'"
	psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
	    CREATE DATABASE $database WITH ENCODING 'utf8';
EOSQL
}

if [[ -n "$CREATE_DB" ]]; then
	echo "Multiple database creation requested: $CREATE_DB"
	for db in $(echo $CREATE_DB | tr ',' ' '); do
		create_database $db
	done
	echo "Multiple databases created"
fi