# Code-quality lens

Search for structural simplifications that preserve behavior while making the change materially smaller, more direct, and easier to extend.

Prioritize:

1. Removing incidental branches, modes, wrappers, or layers through a clearer model.
2. Preventing new spaghetti conditions and scattered feature checks in shared flows.
3. Keeping policy and behavior in the canonical owning module.
4. Replacing cast-heavy, excessively optional, or loosely shaped boundaries with explicit types when justified.
5. Reusing existing canonical helpers instead of adding local variants.
6. Avoiding non-atomic related updates or unnecessary sequential orchestration when the risk is concrete.
7. Challenging very large files or large additions when a cohesive extraction would improve navigation.

Prefer direct, boring code over magic and thin abstractions. At the same time, reject speculative extraction: a different style is not a finding unless the current structure creates a concrete cost or invariant risk.

Be demanding but evidence-driven. Surface major structural issues before smaller modularity or naming concerns. Do not fill a quota.
