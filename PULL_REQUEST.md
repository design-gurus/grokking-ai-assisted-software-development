# Make provider selection extensible

Provider selection was a chain of `if` statements in `providers/base.py`. This introduces a small registry so new backends can be added without touching the factory, with plugin discovery through entry points for backends shipped as separate packages. The mock backend is registered through the new base class to prove the shape; the live backends follow in a later change.

- `providers/registry.py`: `BaseProvider`, `ProviderRegistry`, plugin loading
- `providers/base.py`: `get_provider` consults the registry first
- Tests: the registry resolves the mock and refuses an unknown name
