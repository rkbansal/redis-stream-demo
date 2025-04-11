// app.js - Node.js service that receives client requests and adds them to Redis stream
const express = require('express');
const Redis = require('ioredis');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');

// Initialize Express app
const app = express();
const port = 3000;

// Configure Redis client
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379
});

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(__dirname, 'uploads');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir);
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueFilename = `${uuidv4()}${path.extname(file.originalname)}`;
    cb(null, uniqueFilename);
  }
});

const upload = multer({ 
  storage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
  fileFilter: (req, file, cb) => {
    const allowedTypes = /jpeg|jpg|png|gif/;
    const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
    const mimetype = allowedTypes.test(file.mimetype);
    
    if (extname && mimetype) {
      return cb(null, true);
    } else {
      cb(new Error('Only image files are allowed!'));
    }
  }
});

// Middleware
app.use(express.json());
app.use(express.static('public'));

// Routes
app.post('/process-image', upload.single('image'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image uploaded' });
    }

    // Get processing options from request
    const { operation = 'resize', width, height } = req.body;
    
    // Generate job ID
    const jobId = uuidv4();
    
    // Prepare job data
    const jobData = {
      jobId,
      filePath: req.file.path,
      originalFilename: req.file.originalname,
      operation,
      params: {
        width: width || 800,
        height: height || 600
      },
      timestamp: Date.now()
    };

    // Add job to Redis stream
    await redis.xadd(
      'image-processing-jobs',
      '*',  // Auto-generate ID
      'jobData', JSON.stringify(jobData)
    );

    console.log(`Added job ${jobId} to stream`);
    
    res.status(202).json({ 
      message: 'Image processing job queued',
      jobId,
      status: 'pending'
    });
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: 'Failed to process request' });
  }
});

// Endpoint to check job status
app.get('/job-status/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;
    
    // Check if job result exists in Redis
    const jobResult = await redis.get(`job-result:${jobId}`);
    
    if (!jobResult) {
      return res.status(202).json({ status: 'pending', jobId });
    }
    
    const result = JSON.parse(jobResult);
    res.status(200).json(result);
  } catch (error) {
    console.error('Error:', error);
    res.status(500).json({ error: 'Failed to check job status' });
  }
});

// Start the server
app.listen(port, () => {
  console.log(`Client service listening at http://localhost:${port}`);
});