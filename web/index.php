<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>yt-scribe</title>
    <link rel="stylesheet" href="/css/style.css">
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
</head>
<body>
    <div class="container" x-data="ytScribe()">
        <h1>yt-scribe</h1>
        <p class="subtitle">YouTube transcript fetcher</p>

        <!-- Mode tabs -->
        <div class="tabs">
            <div class="tab" :class="mode === 'search' && 'active'" @click="mode = 'search'">Search</div>
            <div class="tab" :class="mode === 'playlist' && 'active'" @click="mode = 'playlist'">Playlist</div>
        </div>

        <!-- Input -->
        <form class="search-row" @submit.prevent="doSearch">
            <input
                type="text"
                x-model="query"
                :placeholder="mode === 'search' ? 'Search YouTube...' : 'Paste playlist URL...'"
                autofocus
            >
            <button type="submit" :disabled="loading || !query.trim()">
                <span x-show="!loading" x-text="mode === 'search' ? 'Search' : 'Load'"></span>
                <span x-show="loading">Loading...</span>
            </button>
        </form>

        <!-- Error -->
        <div class="error" x-show="error" x-text="error"></div>

        <!-- Results table -->
        <div x-show="results.length > 0" :class="loading && 'loading'">
            <table>
                <thead>
                    <tr>
                        <th><input type="checkbox" :checked="allSelected" @change="toggleAll"></th>
                        <th>#</th>
                        <th>Title</th>
                        <th>Channel</th>
                        <th>Duration</th>
                    </tr>
                </thead>
                <tbody>
                    <template x-for="(v, i) in results" :key="v.video_id">
                        <tr>
                            <td><input type="checkbox" :value="v.video_id" x-model="selected"></td>
                            <td x-text="i + 1"></td>
                            <td x-text="v.title"></td>
                            <td x-text="v.channel || v.uploader || ''"></td>
                            <td x-text="formatDuration(v.duration_seconds || v.duration)"></td>
                        </tr>
                    </template>
                </tbody>
            </table>

            <!-- Bundle name + download -->
            <div class="bundle-row">
                <select x-model="existingBundle" @change="if(existingBundle) bundleName = existingBundle">
                    <option value="">New bundle...</option>
                    <template x-for="b in bundles" :key="b.name">
                        <option :value="b.name" x-text="b.name + ' (' + b.count + ' files)'"></option>
                    </template>
                </select>
                <input
                    type="text"
                    x-model="bundleName"
                    placeholder="Bundle name"
                    :readonly="existingBundle !== ''"
                >
                <button
                    @click="doDownload"
                    :disabled="selectedCount === 0 || !bundleName.trim() || downloading"
                >
                    <span x-show="!downloading">
                        <span x-text="existingBundle ? 'Add' : 'Download'"></span>
                        <span x-text="selectedCount"></span> Selected
                    </span>
                    <span x-show="downloading">Downloading...</span>
                </button>
            </div>
        </div>

        <!-- Download status -->
        <div class="status" x-show="downloadStatus.length > 0">
            <template x-for="s in downloadStatus" :key="s.video_id">
                <div>
                    <span x-text="s.status === 'saved' ? '>' : 'x'"></span>
                    <span x-text="s.title || s.video_id"></span>
                    &mdash;
                    <span x-text="s.status"></span>
                    <span x-show="s.error" x-text="'(' + s.error + ')'"></span>
                </div>
            </template>
        </div>

        <!-- Bundles -->
        <hr>
        <h2 style="font-size:1.1rem; margin-bottom:0.75rem;">Bundles</h2>
        <div x-show="bundles.length === 0" style="font-size:0.85rem; color:#888;">No bundles yet.</div>
        <ul class="bundles-list">
            <template x-for="b in bundles" :key="b.name">
                <li @click="toggleBundle(b)">
                    <strong x-text="b.name"></strong>
                    <span class="meta" x-text="b.count + ' files &middot; ' + b.created_at"></span>
                    <ul class="bundle-files" x-show="b.expanded">
                        <template x-for="f in (b.files || [])" :key="f.filename">
                            <li x-text="f.title || f.filename"></li>
                        </template>
                    </ul>
                </li>
            </template>
        </ul>
    </div>

    <script>
    function ytScribe() {
        return {
            mode: 'search',
            query: '',
            results: [],
            selected: [],
            bundleName: '',
            existingBundle: '',
            loading: false,
            downloading: false,
            downloadStatus: [],
            bundles: [],
            error: '',

            get selectedCount() { return this.selected.length; },
            get allSelected() { return this.results.length > 0 && this.selected.length === this.results.length; },

            toggleAll() {
                if (this.allSelected) {
                    this.selected = [];
                } else {
                    this.selected = this.results.map(v => v.video_id);
                }
            },

            formatDuration(seconds) {
                if (seconds == null || seconds === '') return '';
                seconds = Math.round(Number(seconds));
                if (isNaN(seconds)) return '';
                const h = Math.floor(seconds / 3600);
                const m = Math.floor((seconds % 3600) / 60);
                const s = seconds % 60;
                if (h > 0) {
                    return h + ':' + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
                }
                return m + ':' + String(s).padStart(2, '0');
            },

            autoSlug(text) {
                return text.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '').substring(0, 40);
            },

            async doSearch() {
                this.error = '';
                this.results = [];
                this.selected = [];
                this.downloadStatus = [];
                this.existingBundle = '';
                this.loading = true;

                try {
                    let url;
                    if (this.mode === 'search') {
                        url = '/api/search.php?q=' + encodeURIComponent(this.query) + '&n=10';
                    } else {
                        url = '/api/playlist.php?url=' + encodeURIComponent(this.query);
                    }
                    const resp = await fetch(url);
                    const data = await resp.json();

                    if (!resp.ok) {
                        this.error = data.error || 'Request failed';
                        return;
                    }

                    // search returns array, playlist returns {videos: [...]}
                    this.results = Array.isArray(data) ? data : (data.videos || []);
                    this.bundleName = this.autoSlug(this.mode === 'playlist' ? (data.title || this.query) : this.query);
                } catch (e) {
                    this.error = 'Network error: ' + e.message;
                } finally {
                    this.loading = false;
                }
            },

            async doDownload() {
                this.error = '';
                this.downloadStatus = [];
                this.downloading = true;

                try {
                    const resp = await fetch('/api/stream.php', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            video_ids: this.selected,
                            bundle: this.bundleName
                        })
                    });

                    if (!resp.ok) {
                        const text = await resp.text();
                        try {
                            const data = JSON.parse(text);
                            this.error = data.error || 'Download failed';
                        } catch {
                            this.error = 'Download failed: ' + resp.status;
                        }
                        return;
                    }

                    const reader = resp.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });

                        const lines = buffer.split('\n');
                        buffer = lines.pop();

                        for (const line of lines) {
                            if (!line.startsWith('data: ')) continue;
                            try {
                                const event = JSON.parse(line.slice(6));
                                this.handleStreamEvent(event);
                            } catch {}
                        }
                    }

                    if (buffer.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(buffer.slice(6));
                            this.handleStreamEvent(event);
                        } catch {}
                    }

                    this.loadBundles();
                } catch (e) {
                    this.error = 'Network error: ' + e.message;
                } finally {
                    this.downloading = false;
                }
            },

            handleStreamEvent(event) {
                if (event.event === 'progress') {
                    this.downloadStatus.push({
                        video_id: event.video_id,
                        title: event.title,
                        status: event.status,
                        error: event.error || null,
                    });
                    return;
                }
                if (event.event === 'error') {
                    this.error = event.message || 'Download failed';
                    return;
                }
            },

            async loadBundles() {
                try {
                    const resp = await fetch('/api/bundles.php');
                    const data = await resp.json();
                    this.bundles = (data || []).map(b => ({ ...b, expanded: false, files: null }));
                } catch (e) {
                    // silent
                }
            },

            async toggleBundle(b) {
                if (b.expanded) {
                    b.expanded = false;
                    return;
                }
                try {
                    const resp = await fetch('/api/bundles.php?name=' + encodeURIComponent(b.name));
                    const data = await resp.json();
                    b.files = data.files || [];
                    b.expanded = true;
                } catch (e) {
                    // silent
                }
            },

            init() {
                this.loadBundles();
            }
        }
    }
    </script>
</body>
</html>
