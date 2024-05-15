FROM postgres:15

COPY ./init-db.sql /docker-entrypoint-initdb.d/

ENV POSTGRES_PASSWORD=Qq12345

EXPOSE 5432

CMD [" pg_ctl -D /var/lib/postgresql/data -l logfile start"]
