# Frontend Components Migration Notice

**Date**: 2025-11-21
**Version**: 2.0.0

## 🚀 Important Notice

The frontend components have been migrated to a new unified repository for better organization and maintainability.

### New Repository Location

```
📦 oran-ric-ui (Unified Dashboard)
Location: /home/thc1006/dev/oran-ric-ui
```

## 📋 Migration Summary

### Migrated Components

| Original Location | New Location | Status |
|-------------------|--------------|--------|
| `dashboard/` | `oran-ric-ui/packages/main-dashboard/` | ✅ Migrated |
| `frontend-beam-query/` | `oran-ric-ui/packages/beam-query-ui/` | ✅ Migrated |
| N/A | `oran-ric-ui/packages/shared-components/` | ✨ New |

### What Changed?

#### 1. **Unified Architecture**

The frontend is now organized as a microservices-based monorepo:

- `packages/main-dashboard`: Central control center
- `packages/beam-query-ui`: Beam KPI query interface
- `packages/shared-components`: Shared UI library

#### 2. **Enhanced Features**

- ✨ Material Design 3 implementation
- ✨ Shared component library
- ✨ Unified deployment configurations
- ✨ Comprehensive documentation
- ✨ Development automation scripts

#### 3. **Better Organization**

- Clear separation of concerns
- Independent deployment capability
- Consistent design system
- Improved documentation

## 🔗 Quick Links

### New Repository Structure

```
oran-ric-ui/
├── packages/
│   ├── main-dashboard/        # Dashboard UI
│   ├── beam-query-ui/         # Beam KPI UI
│   └── shared-components/     # Shared library
├── deploy/
│   ├── kubernetes/            # K8s manifests
│   └── docker-compose.yml     # Local development
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   └── DEPLOYMENT.md
└── scripts/                   # Dev automation
```

### Documentation

- **Architecture**: `/home/thc1006/dev/oran-ric-ui/docs/ARCHITECTURE.md`
- **Development Guide**: `/home/thc1006/dev/oran-ric-ui/docs/DEVELOPMENT.md`
- **Deployment Guide**: `/home/thc1006/dev/oran-ric-ui/docs/DEPLOYMENT.md`

### Quick Start

```bash
# Navigate to new repo
cd /home/thc1006/dev/oran-ric-ui

# Run locally
./scripts/run-dev.sh

# Deploy with docker-compose
./scripts/deploy-local.sh

# Build Docker images
./scripts/build-all.sh
```

## 🎯 Migration Benefits

### For Developers

- ✅ **Clearer structure**: Packages are well-organized
- ✅ **Shared components**: Reusable UI library
- ✅ **Better docs**: Comprehensive guides
- ✅ **Automation**: Scripts for common tasks
- ✅ **Modern design**: Material Design 3

### For Operations

- ✅ **Independent deployment**: Each service can be deployed separately
- ✅ **Unified ingress**: Single entry point configuration
- ✅ **Better scaling**: Microservices architecture
- ✅ **Improved monitoring**: Health checks and metrics

### For Users

- ✅ **Consistent UI**: Unified design system
- ✅ **Better UX**: Material Design principles
- ✅ **Faster loading**: Optimized architecture
- ✅ **More features**: Integrated monitoring and management

## 📊 Component Mapping

### Main Dashboard (formerly `dashboard/`)

**Old**: `/home/thc1006/dev/oran-ric-platform/dashboard/`
**New**: `/home/thc1006/dev/oran-ric-ui/packages/main-dashboard/`

**What's New**:
- Material Design UI
- Integrated Beam Query UI (iframe)
- Enhanced xApp management
- Improved logs viewer
- Auto-refresh capability

### Beam Query UI (formerly `frontend-beam-query/`)

**Old**: `/home/thc1006/dev/oran-ric-platform/frontend-beam-query/`
**New**: `/home/thc1006/dev/oran-ric-ui/packages/beam-query-ui/`

**What's New**:
- WSGI-based architecture
- Enhanced proxy server
- Material Design styling
- Better error handling

### Shared Components (NEW!)

**Location**: `/home/thc1006/dev/oran-ric-ui/packages/shared-components/`

**Features**:
- Material Design 3 color system
- O-RAN brand theming
- Reusable components (StatusBadge, StatCard)
- Typography and spacing utilities

## 🔄 Transition Plan

### Phase 1: Coexistence (Current)

- Both repos exist simultaneously
- Original frontend components remain for backward compatibility
- New development happens in `oran-ric-ui`

### Phase 2: Deprecation (Future)

- Original frontend directories marked as deprecated
- README added with links to new repo
- No new features in old location

### Phase 3: Removal (TBD)

- After testing and validation
- Original directories removed
- Migration complete

## 📝 Action Items

### For Current Users

1. Review new repository structure
2. Update bookmarks and documentation
3. Test new deployment methods
4. Provide feedback on new features

### For Developers

1. Clone new repository: `/home/thc1006/dev/oran-ric-ui`
2. Read development guide: `docs/DEVELOPMENT.md`
3. Update CI/CD pipelines (if applicable)
4. Submit PRs to new repository

### For DevOps

1. Review deployment configurations
2. Update Kubernetes manifests
3. Test new deployment workflow
4. Update monitoring and alerting

## ❓ FAQ

### Q: Do I need to migrate my custom changes?

**A**: If you have custom modifications in the original `dashboard/` or `frontend-beam-query/`, you should migrate them to the new repo. Refer to `docs/DEVELOPMENT.md` for guidance.

### Q: Will the old frontend continue to work?

**A**: Yes, the original frontend will continue to work during the transition period. However, new features will only be added to the new unified dashboard.

### Q: How do I report issues?

**A**: For issues with the new unified dashboard, create issues in the new repository. For the original frontend, continue using the existing process.

### Q: What about `frontend/` (Kubernetes Dashboard)?

**A**: The `frontend/` directory (Kubernetes Dashboard) remains unchanged. It's a separate tool and is not part of this migration.

## 📞 Support

For questions or assistance with the migration:

- **Developer**: thc1006
- **Documentation**: `/home/thc1006/dev/oran-ric-ui/docs/`
- **Issues**: Create issue in appropriate repository

## 🎉 Thank You

Thank you for your patience during this migration. The new unified dashboard provides a better foundation for future development and an improved experience for all users.

---

**Migration Date**: 2025-11-21
**Version**: 2.0.0
**Status**: ✅ Complete
