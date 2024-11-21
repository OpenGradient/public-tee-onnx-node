# A Go base image is enough to build nitriding reproducibly.
# We use a specific instead of the latest image to ensure reproducibility.
FROM golang:1.22 as builder

WORKDIR /

# Clone the repository and build the stand-alone nitriding executable.
RUN git clone https://github.com/brave/nitriding-daemon.git
ARG TARGETARCH
RUN ARCH=${TARGETARCH} make -C nitriding-daemon/ nitriding

# Use the intermediate builder image to add our files.  This is necessary to
# avoid intermediate layers that contain inconsistent file permissions.
COPY server.py start.sh utils.py /bin/
COPY storage/storage.py storage/__init__.py /bin/storage/
# COPY storage/models/ /bin/storage/models/
RUN chown root:root /bin/server.py /bin/start.sh
RUN chmod 0755      /bin/server.py /bin/start.sh

FROM python:3.12-slim-bullseye

# Set environment variables for IPFS
ENV IPFS_VERSION=0.19.1
ENV IPFS_PATH=/root/.ipfs
ENV LIBP2P_FORCE_PNET=1

# Install necessary tools for IPFS and clean up
RUN apt-get update && apt-get install -y \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Download and install IPFS
RUN wget https://dist.ipfs.io/go-ipfs/v${IPFS_VERSION}/go-ipfs_v${IPFS_VERSION}_linux-amd64.tar.gz \
    && tar -xvzf go-ipfs_v${IPFS_VERSION}_linux-amd64.tar.gz \
    && cd go-ipfs \
    && ./install.sh \
    && cd .. \
    && rm -rf go-ipfs go-ipfs_v${IPFS_VERSION}_linux-amd64.tar.gz

# Create the IPFS data directory and initialize IPFS
RUN mkdir -p $IPFS_PATH && ipfs init

# Copy the swarm.key file
COPY swarm.key $IPFS_PATH/swarm.key

# Modify IPFS config to disable announcing on the DHT and only listen on localhost for the API
RUN ipfs config --json Addresses.Announce "[]" && \
    ipfs config Addresses.API "/ip4/127.0.0.1/tcp/5001" && \
    ipfs config Addresses.Gateway "/ip4/127.0.0.1/tcp/8081"

# Add the bootstrap node
RUN ipfs bootstrap rm --all && \
    ipfs bootstrap add /ip4/3.140.191.156/tcp/4001/p2p/12D3KooWQWntZ1RYAxBtqbPcRz1e24o9xzXkvieJnhhNAC6xKwAF

# Copy all our files to the final image.
COPY --from=builder /nitriding-daemon/nitriding /bin/start.sh /bin/server.py /bin/utils.py /bin/
COPY --from=builder /bin/storage/__init__.py /bin/storage/storage.py /bin/storage/

# Copy requirements file into final image
COPY requirements.txt /app/requirements.txt

# Install the required Python packages.
RUN pip install --no-cache-dir -r /app/requirements.txt

# Set working directory
WORKDIR /bin

# Expose port 8000 for flask server
EXPOSE 443
EXPOSE 8000
EXPOSE 5001

CMD ["start.sh"]
