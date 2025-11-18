FROM apache/nifi:1.25.0

# Create directories as root
RUN mkdir -p /opt/nifi/nifi-current/conf \
    /opt/nifi/nifi-current/data \
    /opt/nifi/nifi-current/flowfile_repository \
    /opt/nifi/nifi-current/content_repository \
    /opt/nifi/nifi-current/database_repository \
    /opt/nifi/nifi-current/state

# Copy default nifi.properties from base image if it exists
RUN if [ -f /opt/nifi/nifi-current/conf/nifi.properties ]; then \
      cp /opt/nifi/nifi-current/conf/nifi.properties /opt/nifi/nifi-current/conf/nifi.properties.bak; \
    fi

# Ensure nifi.properties exists (create empty if missing)
RUN touch /opt/nifi/nifi-current/conf/nifi.properties

# Set permissions while still root
RUN chown -R nifi:nifi /opt/nifi/nifi-current && \
    chmod -R 755 /opt/nifi/nifi-current && \
    chmod 644 /opt/nifi/nifi-current/conf/nifi.properties

USER nifi
CMD ["/opt/nifi/scripts/start.sh"]