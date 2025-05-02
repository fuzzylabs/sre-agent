ARG VERSION="dev"
# This is the version of the commit that was built
ARG COMMIT="92d95e4dbe841e9e3b8c6741ffdcfbff300870d2"

FROM golang:1.24.2 AS build
# allow this step access to build arg
ARG VERSION
ARG COMMIT
# Set the working directory
WORKDIR /build

RUN go env -w GOMODCACHE=/root/.cache/go-build

# Install dependencies
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/root/.cache/go-build go mod download

COPY . ./
# Build the server
RUN --mount=type=cache,target=/root/.cache/go-build CGO_ENABLED=0 go build -ldflags="-s -w -X main.version=${VERSION} -X main.commit=${COMMIT} -X main.date=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    -o github-mcp-server cmd/github-mcp-server/main.go

# Make a stage to run the app
FROM gcr.io/distroless/base-debian12
# Set the working directory
WORKDIR /server
# Copy the binary from the build stage
COPY --from=build /build/github-mcp-server .
# Command to run the server
CMD ["./github-mcp-server", "sse"]
