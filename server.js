const express = require('express');
const fs = require('fs');
const path = require('path');
const app = express();
const PORT = 3000;

const sqlite3 = require('sqlite3').verbose();
const DB_PATH = path.join(__dirname, 'media_metadata.db');
const db = new sqlite3.Database(DB_PATH);

app.use(express.json());
app.use(express.static(__dirname));

const videoConfig = require('./video_config.json');
const VIDEO_DIR = videoConfig.videoDir;
const VIDEO_EXTENSIONS = ['.mp4', '.mkv', '.webm', '.avi', '.mov'];

// List local video files
function findVideosRecursive(dir) {
	let results = [];
	const list = fs.readdirSync(dir);
	list.forEach(file => {
		const filePath = path.join(dir, file);
		const stat = fs.statSync(filePath);
		if (stat && stat.isDirectory()) {
			results = results.concat(findVideosRecursive(filePath));
		} else if (VIDEO_EXTENSIONS.includes(path.extname(file).toLowerCase())) {
			results.push({
				title: path.parse(file).name,
				filename: path.relative(VIDEO_DIR, filePath)
			});
		}
	});
	return results;
}

app.get('/api/videos', (req, res) => {
	try {
		const videos = findVideosRecursive(VIDEO_DIR);
		res.json({ videos });
	} catch (err) {
		res.status(500).json({ error: 'Failed to read video directory.' });
	}
});

// List TV shows (folders) and top-level videos
function getShowsAndMovies(dir) {
    const items = fs.readdirSync(dir);
    let shows = [];
    let movies = [];
    items.forEach(item => {
        const itemPath = path.join(dir, item);
        const stat = fs.statSync(itemPath);
        if (stat.isDirectory()) {
            shows.push({
                title: item,
                folder: item
            });
        } else if (VIDEO_EXTENSIONS.includes(path.extname(item).toLowerCase())) {
            movies.push({
                title: path.parse(item).name,
                filename: item
            });
        }
    });
    return { shows, movies };
}

app.get('/api/shows', (req, res) => {
    try {
        const { shows, movies } = getShowsAndMovies(VIDEO_DIR);
        res.json({ shows, movies });
    } catch (err) {
        res.status(500).json({ error: 'Failed to read video directory.' });
    }
});

app.get('/api/seasons', (req, res) => {
    const show = req.query.show;
    if (!show) return res.status(400).json({ error: 'Missing show parameter.' });
    const showPath = path.join(VIDEO_DIR, show);
    if (!fs.existsSync(showPath)) return res.status(404).json({ error: 'Show not found.' });
    const items = fs.readdirSync(showPath);
    const seasons = items.filter(item => fs.statSync(path.join(showPath, item)).isDirectory());
    res.json({ seasons });
});

app.get('/api/metadata', (req, res) => {
  let file = req.query.file;
  if (!file) return res.status(400).json({ error: 'Missing file parameter.' });
  // Convert relative path to absolute path
  if (!file.startsWith('/')) {
    file = path.join(VIDEO_DIR, file);
  }
  console.log('Looking up metadata for file_path:', file);
  db.get('SELECT * FROM media WHERE file_path = ?', [file], (err, row) => {
    if (err) return res.status(500).json({ error: 'DB error.' });
    if (!row) return res.status(404).json({ error: 'Metadata not found.' });
    res.json(row);
  });
});

app.get('/api/episodes', (req, res) => {
    const show = req.query.show;
    const season = req.query.season;
    if (!show || !season) return res.status(400).json({ error: 'Missing show or season parameter.' });
    const seasonPath = path.join(VIDEO_DIR, show, season);
    if (!fs.existsSync(seasonPath)) return res.status(404).json({ error: 'Season not found.' });
    const items = fs.readdirSync(seasonPath);
    const episodes = items.filter(item => VIDEO_EXTENSIONS.includes(path.extname(item).toLowerCase()))
        .map(item => ({
            title: path.parse(item).name,
            filename: path.join(show, season, item)
        }));
    res.json({ episodes });
});

// Serve video files using a regex route for compatibility
app.get(/^\/videos\/(.+)$/, (req, res) => {
    const filePath = path.join(VIDEO_DIR, req.params[0]);
    if (!fs.existsSync(filePath)) return res.status(404).send('File not found');
    res.sendFile(filePath);
});

app.get('/api/showinfo', (req, res) => {
  const folder = req.query.folder;
  if (!folder) return res.status(400).json({ error: 'Missing folder parameter.' });
  db.get('SELECT * FROM shows WHERE folder = ?', [folder], (err, row) => {
    if (err) return res.status(500).json({ error: 'DB error.' });
    if (!row) return res.status(404).json({ error: 'Show info not found.' });
    res.json(row);
  });
});

app.listen(PORT, () => {
	console.log(`Server running at http://localhost:${PORT}`);
});
