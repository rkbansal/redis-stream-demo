# Redis Streams Image Processing Service

This project demonstrates inter-service communication using Redis Streams with a Node.js client-facing service and a Python image processing worker.

## Architecture Overview

![Architecture Diagram](https://mermaid.ink/img/pako:eNptUc1qwzAMfhWhuXhQ6Ba2Q1l32GGDwUK30wxj1G4RjZ3FckkJ4XcfSUrb0YMtf_r0Wxai9R6FEQGI1hZt90QvA9mzVr0-eDJ0hx3lmYC10XzAbSvgeYkzX8AwbGbzBWzBwkwQAj3pPEFUTHjXBPVhjdmGCXYZeQKuSE46KGWNhxkM3CwWG0Gag9qJPnPBpzL_15uf8xUUQSXDlWzWPuoSF-Xc-3g9tKZLOSZlAYZrFJmkZU7l_J1FVgzTLPvkAcJO4HMcTGFvGE9R-hYm2UuCf4yvUSKdm9TpFjyO-oy0L7I_O5B2fVX7A89Nzr2QaeSP-9RzA_mUd7EIU30fXLdW3YXF5GnwfGNuYELVejDZVP8CgOKHtw)

## Components

### 1. Node.js Client-Facing Service

A REST API service built with Express that:

- Accepts image upload requests from clients
- Stores uploaded images locally
- Adds processing jobs to Redis Stream
- Provides endpoints to check job status

### 2. Redis Streams

Acts as the communication medium between services:

- Maintains a stream of image processing jobs
- Supports consumer groups for parallel processing
- Provides persistence and reliability

### 3. Python Worker Service

A background service that:

- Subscribes to the Redis Stream as part of a consumer group
- Claims and processes image operations (resize, grayscale, blur)
- Stores processed images
- Updates job status in Redis

## Setup Instructions

### Prerequisites

- Docker and Docker Compose
- Node.js 14+ (for local development)
- Python a 3.8+ (for local development)

### Project Structure

```
redis-image-processing/
├── node-service/
│   ├── app.js
│   ├── package.json
│   ├── Dockerfile
│   └── public/
│       └── index.html
├── python-worker/
│   ├── worker.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

### Running with Docker Compose

1. Clone the repository:

```bash
git clone <repository-url>
cd redis-image-processing
```

2. Start the services:

```bash
docker-compose up -d
```

3. Access the web interface:
   Open your browser and go to `http://localhost:3000`

### Running Locally (Development)

#### Node.js Service

```bash
cd node-service
npm install
npm start
```

#### Python Worker

```bash
cd python-worker
pip install -r requirements.txt
python worker.py
```

#### Redis

Make sure Redis is running locally on port 6379.

## Usage

1. Open the web interface at `http://localhost:3000`
2. Upload an image and select a processing operation
3. Submit the form to start processing
4. The page will automatically check the job status and display the processed image when ready

## Scaling Considerations

This architecture can be scaled by:

- Running multiple Python worker instances
- Running multiple Node.js service instances with a load balancer
- Using Redis Cluster for higher throughput and reliability
- Implementing separate streams for different processing operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
