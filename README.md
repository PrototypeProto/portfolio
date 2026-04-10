# Personal Website (portfolio) + my network forum

## This is a personal project where I develop my portfolio with the addition of it primarily serving as a place to share things with friends and people I approve in my network.

### The portfolio is accessible to the public
Includes:
<ul>
    <li>Projects & Video demo</li>
    <li>Other links (GitHub, LinkedIn, Contact Details, etc.)</li>
    <li>Maybe more/snippets of what is currently hidden</li>
</ul>

### Everything else -- For the most part-- is restricted to people who I have approved.
<ul>
    <li>Web forum</li>
    <li>Personal media (clips, long videos, YT videos I want to share)</li>
    <li>Temporary file storage (for convenience and privacy) -- restricted to only high trust friends</li>
    <li>more...</li>
</ul>


### Tech used:
<ul>
    <li><b>React</b> (v???)</li>
    <li><b>Python</b> (3.14.2)</li>
    <li><b>SQLAlchemy</b> (Python SQL toolkit and Object Relational Mapper)</li>
    <li><b>Alembic</b> (Database migration tool)</li>
    <li><b>PostgreSQL</b> (SQL database)</li>
    <li><b>Redis</b> (In-memory database)</li>
    <li><b>Docker</b> Containerized applications</li>
    <li>... and many more libraries to provide greater functionality and security</li>
</ul>

## TODO: Backend
<ol>
    <li>Security</li>
    <li>Auth Design</li>
    <li>Configs & Secrets</li>
    <li>Architecture & Code Structure</li>
        <ul>
            <li>Separate user vs server errors</li>
            <li>Custom errors & Error handling</li>
            <li>Ensure safe database transactions, rolling back on failures</li>
        </ul>
    <li>Redis & Cachine</li>
    <li>TempFS file upload</li>
        <ul>
            <li>POST /tempfs/files/{id}/unlock: to get short-lived download token</li>
            <li> in the "compress on the fly" path, compressor.write(chunk) returns the number of bytes consumed by the internal buffer, not the compressed bytes — and yielding that integer from a generator will crash StreamingResponse.</li>
            <li></li>
        </ul>
    <li>Frontend auth state</li>
    <li>Deployment</li>
        <ul>
            <li>SSL certificates & automation</li>
        </ul>
    <li>Security: </li>
        <ul>
            <li>Path traversal</li>
            <li>SQL injection</li>
            <li>XSS / HTML formatted forum message text</li>
            <li>General sanitization from user input</li>
            <li>Unsanitized filenames</li>
            <li></li>
            <li></li>
        </ul>
    <li>DB triggers for when user changes vote: like->dis / dis->like</li>
    <li></li>
    <li></li>
</ol>

## TODO: Frontend
<ul>
    <li>useMedia.ts: Implement fetching page ct</li>
    <li>authContext: implement cookie storage for persistence and automatic retrieval/expiration</li>
    <li></li>
    <li></li>
    <li></li>
    <li></li>
    <li></li>
    <li></li>
</ul>

# NOTES:
