# CHANGELOG


## v1.4.4 (2026-03-21)

### Bug Fixes

- **ci**: Prevent re-publishing already-released versions to PyPI
  ([`e76cc06`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/e76cc0624ec88cb31d3f5548a0dd3ec80b6bac51))

### Documentation

- Standardize README integration options to pip, docker, and uv
  ([`9ca4d6e`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/9ca4d6e24d8a0a51ade74d844b7afc6e4a20a419))


## v1.4.3 (2026-03-21)

### Bug Fixes

- Correct PSR v10 changelog config and remove deprecated --noop flag
  ([`74198f0`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/74198f0e489ea7d3f0140260460367cac0cdd891))


## v1.4.2 (2026-03-21)

### Bug Fixes

- Add changelog entry for Codex installation methods update
  ([`56f0d17`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/56f0d17b471b38caab82fd353bb5f17fe39c0eea))

- Move changelog_file to correct PSR config section
  ([`7d21024`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/7d210246192c6bc1f3627ea980c4e89408f921e4))


## v1.4.1 (2026-03-21)

### Bug Fixes

- Add all installation methods for Codex section in README
  ([`28c05b7`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/28c05b7d38edecf7041c4dce60935562caf6744e))

### Documentation

- Fix Codex installation steps to use uvx instead of local path
  ([`0043ab5`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/0043ab5813548fb82b29da57592bd66a60c95094))


## v1.4.0 (2026-03-21)

### Bug Fixes

- Address PR review feedback — deduplicate config, harden release workflow
  ([`7db6203`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/7db6203ff0c7e4c34ef434c17e165a5b65a23b86))

- Harden release workflow with correct PSR flags and safeguards
  ([`abae0bd`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/abae0bd6c0848b4443b6f9fff36d825dedba4626))

- Remove empty changelog section header from pyproject.toml
  ([`cae2ca8`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/cae2ca89cb354fd0830662793a4392f0809e58d8))

- Replace invalid PSR flags with direct git/gh commands
  ([`4d386cf`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/4d386cf7d24efa51ac044de9806019d3513d5edb))

- Resolve lint errors, apply ruff formatting, correct tool count
  ([`8362f7c`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/8362f7c339d58dc3d7a54d7a6d10a02629438b73))

- Use correct PSR flags for release workflow
  ([`d595457`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/d59545754381694e3a7fbf319aaefd4e48839865))

- Use correct semantic-release version --print flag
  ([`d967a08`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/d967a0805e80774a7591f3ee5aaf93e1d69d7cd4))

- Use master branch instead of main across all configs
  ([`c54e2af`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/c54e2af42cd2cf1da6690a649965343e3e1cbf7d))

- **ci**: Checkout master branch instead of SHA to fix detached HEAD in release workflow
  ([`4b07982`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/4b07982b2e79ebdf782c6df3d3808d65ae4ca102))

### Documentation

- Add CODE_OF_CONDUCT.md and fix author name typo
  ([`f014e3c`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/f014e3c3f9c3c79c4cd52ba6321ecd28757425e3))

- Add GitHub issue and PR templates
  ([`518a483`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/518a4832b0cbbc7d9ce671a7318d592b1bd7b385))

- Update all documentation for production PyPI publishing
  ([`0f6cadb`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/0f6cadb66070f7a3dd0f5e57bbeedee7bca1f72a))

### Features

- Add production-grade PyPI publishing with Python Semantic Release
  ([`8b47143`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/8b47143379e19c7e45b2cc2724be26673b5e80bf))

- Rename PyPI package to bitbucket-server-mcp
  ([`77f0e93`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/77f0e9322f26ed369076944174b44d91384230cb))

- Update repo URLs to bitbucket-server-mcp
  ([`c3a6fab`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/c3a6fabf5e0fde8b7cb3ae00565fc5a74b79c587))


## v1.3.1 (2026-03-21)

### Bug Fixes

- Correct test to match HTTPS-only enforcement
  ([`249a257`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/249a25700442300b436383ebb1e12a974df6437b))

### Chores

- Add MIT license and bump version to 1.3.1
  ([`41d1e66`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/41d1e6650d9e1f395eaf61d29dbed7a990b60972))


## v1.3.0 (2026-03-21)

### Features

- Enforce HTTPS-only for Bitbucket Server connections
  ([`edc8286`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/edc8286793a15425ff70f8f22576064630b02fd6))


## v1.2.0 (2026-03-20)

### Chores

- Bump version to 1.2.0
  ([`e8b7032`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/e8b7032cf60c8a391c6789972770ec3aba9ffadd))

### Documentation

- Remove manual running section from README
  ([`271d6cc`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/271d6cc395d1be72252e1316cd7245281d2510b4))

- Update CHANGELOG with v1.2.0 release notes
  ([`c03d2d0`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/c03d2d040b09f91d98ab5b230f11b0fe48a13bad))

### Features

- Add Docker support for running MCP server in a container
  ([`5c470e7`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/5c470e79bd12238a7468571f8e86ef88162ba941))


## v1.1.1 (2026-03-20)

### Documentation

- Add SECURITY_REVIEW.md and CONTRIBUTING.md
  ([`4b723e2`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/4b723e244a5cc1dd46cebab352e129d5ce6ba6e4))

### Features

- Add dashboard, user search, attachments, PR workflow tools and search fallback
  ([`d0f1b8c`](https://github.com/ManpreetShuann/bitbucket-server-mcp/commit/d0f1b8cb9355cfe0a196c5583d2cf820bf114c76))


## v1.0.0 (2026-03-20)

- Initial Release
