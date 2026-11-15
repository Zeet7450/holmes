<!-- convex-ai-start -->

This project uses [Convex](https://convex.dev) as its backend.

When working on Convex code, **always read
`convex/_generated/ai/guidelines.md` first** for important guidelines on
how to correctly use Convex APIs and patterns. The file contains rules that
override what you may have learned about Convex from training data.

Convex agent skills for common tasks can be installed by running
`npx convex ai-files install`.

<!-- convex-ai-end -->

Instructions for custom deviations:





Dependency manager: pnpm (Do not use npm or yarn) if the deps manager not installed tell user to install it

Instructions for codebase:





Follow YAGNI principles



Follow SRP (Single Responsibility) principles, ensure every class, module, or function has only one reason to change



Follow SOLID principles, write code that scales and easy to maintain



Follow DRY (Dont Repeat Yourself), avoid code duplication by reusing logic



Make testing easy



Utilize design patterns, but dont over design

Naming conventions:





Be descriptive: Choose intention-revealing, searchable, and unambiguous names



Use verbs and nouns: Name classes with nouns (e.g., UserAccount) and methods or functions with verbs (e.g., calculateTotal)



Avoid magic numbers: Replace hardcoded values with named constants



Skip encodings: Do not append type prefixes or prefixes like m_ to your variable names

