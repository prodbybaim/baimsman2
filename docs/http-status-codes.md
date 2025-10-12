# HTTP Status Codes

Comprehensive reference of HTTP status codes grouped by class (1xx–5xx). Each code includes the standard reason phrase and a short description.

## Informational 1xx

- **100 Continue** — Client may continue with the request (server received headers and requests the body).
- **101 Switching Protocols** — Server switches protocol as requested by the client (e.g., upgrade to WebSocket).
- **102 Processing** (WebDAV) — Server has accepted the request but processing is not complete.
- **103 Early Hints** — Preliminary headers to help the client start fetching resources while the final response is prepared.

## Successful 2xx

- **200 OK** — Request succeeded; response body contains the representation.
- **201 Created** — Resource successfully created (usually includes `Location` header pointing to new resource).
- **202 Accepted** — Request accepted for processing, but not completed yet.
- **203 Non-Authoritative Information** — Returned meta-information from a local or third-party copy, not the origin server.
- **204 No Content** — Request succeeded but there's no content to return.
- **205 Reset Content** — Instructs client to reset the document view; no response body.
- **206 Partial Content** — Partial resource returned due to `Range` header (for resumable downloads).
- **207 Multi-Status** (WebDAV) — Multiple independent operations' status (XML body).
- **208 Already Reported** (WebDAV) — Members of a DAV binding already reported in previous response.
- **226 IM Used** — Server fulfilled a GET and the response is a representation of the result of one or more instance-manipulations.

## Redirection 3xx

- **300 Multiple Choices** — Multiple representations available; client or user should choose one.
- **301 Moved Permanently** — Resource permanently moved to another URI.
- **302 Found** — Temporarily moved; historically ambiguous with method handling.
- **303 See Other** — Client should retrieve the resource using GET at the `Location` URI.
- **304 Not Modified** — Resource has not changed since the last request (conditional GET and caching).
- **305 Use Proxy** — Resource must be accessed through the proxy given by the `Location` header (deprecated/rare).
- **306 (Unused)** — Formerly "Switch Proxy"; no longer used.
- **307 Temporary Redirect** — Temporary redirect that preserves the request method and body.
- **308 Permanent Redirect** — Permanent redirect that preserves the request method and body.

## Client Error 4xx

- **400 Bad Request** — Malformed request syntax or invalid request.
- **401 Unauthorized** — Authentication required (client is unauthenticated). Include `WWW-Authenticate` header.
- **402 Payment Required** — Reserved for future digital payment use (rarely used).
- **403 Forbidden** — Server understood request but refuses to authorize it.
- **404 Not Found** — Resource not found at the given URI.
- **405 Method Not Allowed** — HTTP method not supported by the resource (server should return `Allow` header).
- **406 Not Acceptable** — Content negotiation failed; server cannot produce a response matching `Accept` headers.
- **407 Proxy Authentication Required** — Client must authenticate with the proxy.
- **408 Request Timeout** — Client did not produce a request within the server's time window.
- **409 Conflict** — Request conflicts with the current state of the resource.
- **410 Gone** — Resource permanently gone; no forwarding address known.
- **411 Length Required** — Server requires `Content-Length` header and it is missing.
- **412 Precondition Failed** — A condition in headers (If-Match, If-Unmodified-Since, etc.) failed.
- **413 Payload Too Large** — Request entity is larger than server is willing or able to process.
- **414 URI Too Long** — Request URI is longer than the server can interpret.
- **415 Unsupported Media Type** — Request contains an unsupported media type.
- **416 Range Not Satisfiable** — Unsatisfiable `Range` header.
- **417 Expectation Failed** — Server cannot meet the requirements of the `Expect` header.
- **418 I'm a teapot** — April Fools' joke from RFC 2324 (sometimes used playfully).
- **421 Misdirected Request** — Request directed at a server that is not able to produce a response.
- **422 Unprocessable Entity** (WebDAV) — Semantic errors in request content (validation errors).
- **423 Locked** (WebDAV) — Resource is locked.
- **424 Failed Dependency** (WebDAV) — Request failed because a previous dependent request failed.
- **425 Too Early** — Server is unwilling to risk processing a request that might be replayed.
- **426 Upgrade Required** — Client should switch to a different protocol.
- **428 Precondition Required** — Server requires the request to be conditional.
- **429 Too Many Requests** — Rate limiting; client sent too many requests in a given time window.
- **431 Request Header Fields Too Large** — Header fields are too large or too many.
- **451 Unavailable For Legal Reasons** — Resource unavailable due to legal reasons (e.g., censorship).

## Server Error 5xx

- **500 Internal Server Error** — Generic server error; unexpected condition prevented fulfilling the request.
- **501 Not Implemented** — Server lacks the ability to fulfill the request (unknown method).
- **502 Bad Gateway** — Invalid response received from upstream server while acting as a gateway or proxy.
- **503 Service Unavailable** — Server currently unable to handle the request (overloaded or down for maintenance).
- **504 Gateway Timeout** — Gateway timed out waiting for upstream server.
- **505 HTTP Version Not Supported** — Server does not support the HTTP protocol version used in the request.
- **506 Variant Also Negotiates** — Transparent content negotiation resulted in circular reference.
- **507 Insufficient Storage** (WebDAV) — Server is unable to store the representation needed to complete the request.
- **508 Loop Detected** (WebDAV) — Server terminated operation because it encountered an infinite loop while processing.
- **510 Not Extended** — Further extensions to the request are required for the server to fulfill it.
- **511 Network Authentication Required** — Client needs to authenticate to gain network access (e.g., captive portal).

## Notes and tips

- For APIs: commonly used: `200`, `201`, `204`, `400`, `401`, `403`, `404`, `409`, `415`, `422`, `429`, `500`, `502`, `503`, `504`.
- Use `201` plus `Location` for creation, `204` for successful requests that return no body (e.g., DELETE).
- Use `4xx` for client-side errors and `5xx` for server-side failures.
- `304 Not Modified` is critical for caching and bandwidth savings when using conditional requests.
- When exposing custom errors, return a clear machine-readable JSON body {"code":"...","message":"..."} in addition to the HTTP status code.

---

If you want the file in a different path or a shortened cheatsheet version, tell me where and I'll update it.