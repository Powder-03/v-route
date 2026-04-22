FROM golang:alpine AS builder

WORKDIR /app

# Copy all source code first
COPY . .

# Run go get to explicitly fetch the dependencies inside the container 
# since the host machine might not have Go installed to run `go mod tidy`
RUN go get github.com/segmentio/kafka-go github.com/jackc/pgx/v5 github.com/jackc/pgx/v5/pgxpool && go mod tidy

# Build statically compiled binary
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -ldflags="-w -s" -o go_worker cmd/worker/main.go

# Second Stage: pure minimal scratch image
FROM scratch

WORKDIR /root/

# Copy the pre-built binary from the builder stage
COPY --from=builder /app/go_worker .

# Copy root certificates as scratch provides none 
# This is necessary for SSL connections (like connecting to a managed Postgres if needed later)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

# Exec the binary
CMD ["./go_worker"]
