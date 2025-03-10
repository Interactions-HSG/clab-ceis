FROM ontotext/graphdb:10.7.3

COPY conf/ceis-dev-local-repo.ttl /opt/ceis-dev-local-repo.ttl
COPY entrypoint.sh /opt/entrypoint.sh

RUN chmod 755 /opt/entrypoint.sh

ENTRYPOINT [ "/opt/entrypoint.sh" ]