FROM golang:1.22-alpine AS builder

WORKDIR /app

# Copy dependency manifests first to leverage Docker cache layer
COPY go.mod go.sum* ./
RUN go mod download

# Copy the rest of the application source code
COPY . .

# Build statically compiled binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags="-w -s" -o go_worker cmd/worker/main.go

# Second Stage: pure minimal scratch image
FROM scratch

WORKDIR /root/

# Copy the pre-built binary from the builder stage
COPY --from=builder /app/go_worker .

# Copy timezone data & root certificates as scratch provides none 
# This is necessary for SSL connections (like connecting to a managed Postgres if needed later)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/zoneinfo /usr/share/zoneinfo

# Exec the binary
CMD ["./go_worker"]
