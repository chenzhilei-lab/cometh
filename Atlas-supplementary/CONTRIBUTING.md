# Contributing to COMETH

Thanks for your interest in contributing. COMETH is an independent research project that welcomes community involvement.

## Ways to Contribute

### 🐛 Bug Reports
- Use GitHub Issues with `[BUG]` prefix
- Include: OS, PyTorch version, GPU model, minimal reproduction script, expected vs actual output

### 📊 Benchmark Submissions
COMETH maintains a **Community Benchmark Protocol**. To submit your method's results:
1. Run your method against the benchmark dataset (see `configs/benchmark/`)
2. Open an issue with `[BENCHMARK]` prefix
3. Attach results in the specified JSON format
4. We'll add them to the public leaderboard

### 🔧 Pull Requests
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Run the demo notebook to verify nothing breaks (`notebooks/demo_workflow.ipynb`)
5. Submit a PR with a clear description

### 💡 Feature Requests
- Use `[FEATURE]` prefix in Issues
- Describe the use case and expected behavior

## Development Setup

```bash
git clone https://github.com/cometh-project/cometh.git
cd cometh
pip install -r requirements.txt
pip install -e .  # editable install for development
```

## Code Style
- Follow PEP 8
- Type hints encouraged for public APIs
- Docstrings in NumPy style
- Keep imports sorted: stdlib → third-party → local

## License
All contributions are accepted under the project's dual license (MIT for non-commercial / commercial license available). See [LICENSE](LICENSE).
