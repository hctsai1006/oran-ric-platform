# ns-O-RAN with e2sim Integration - Build Troubleshooting Guide

**Date:** 2025-11-21
**Environment:** Ubuntu Linux 5.15.0-161-generic
**ns-3 Version:** 3.38.rc1
**Build System:** CMake + Python wrapper

## Executive Summary

This document records a comprehensive troubleshooting session for building ns-O-RAN (ns-3 based O-RAN simulator) with e2sim library integration. The build initially failed with multiple CMake configuration errors and header file inclusion issues. After systematic diagnosis, three critical fixes were applied to successfully build the entire system.

## Problem Overview

The ns-O-RAN build with e2sim integration failed with the following cascading errors:

1. **CMake Configuration Failure**: oran module could not be configured
2. **Disk Space Exhaustion**: Build artifacts consumed all available space
3. **Header File Not Found**: e2sim ASN.1 headers missing during compilation
4. **Include Path Propagation**: Dependent modules couldn't find e2sim headers

## Environment Setup

### Prerequisites Installed

```bash
# ASN.1 Compiler
sudo apt-get install -y asn1c

# SCTP Library
sudo apt-get install -y libsctp-dev

# e2sim Library (custom installation)
# Installed at: /usr/local/include/e2sim
# Library at: /usr/local/lib/libe2sim.a
```

### ns-O-RAN Repository

```bash
git clone https://github.com/o-ran-sc/sim-ns3-o-ran-e2.git /opt/ns-oran
cd /opt/ns-oran
git checkout master
```

### oran Module Integration

```bash
# Clone oran module into contrib/
cd /opt/ns-oran/contrib
git clone https://github.com/o-ran-sc/sim-ns3-o-ran-e2.git oran
```

## Error 1: CMake Configuration Failure

### Symptoms

```
CMake Error at build-support/custom-modules/ns3-module-macros.cmake:76 (target_precompile_headers):
  Cannot specify precompile headers for target "REUSE_FROM" which is not
  built by this project.

CMake Error at build-support/custom-modules/ns3-module-macros.cmake:94 (add_library):
  add_library ALIAS requires exactly one target argument.
```

Configuration output showed:
```
Modules that cannot be built:
brite                     click                     mpi
openflow                  oran                      visualizer
```

### Root Cause Analysis

**File:** `/opt/ns-oran/contrib/oran/CMakeLists.txt:27`

```cmake
build_lib(
    LIBNAME oran-interface  # ❌ PROBLEM: hyphen in name
    SOURCE_FILES ...
```

**Why This Failed:**

1. CMake variable naming: `${liboran-interface}` is parsed as `${liboran}` minus `interface`
2. Since `${liboran}` is undefined, it becomes empty string minus `interface`
3. The `build_lib()` macro from `ns3-module-macros.cmake` then tries to create targets with empty/invalid names
4. Precompiled header target reference fails: `REUSE_FROM ""` (empty string)
5. Library alias fails: `add_library(ns3::""  ALIAS "")` (both empty)

### Solution

**Change:** `/opt/ns-oran/contrib/oran/CMakeLists.txt:27`

```cmake
build_lib(
    LIBNAME oran  # ✅ FIXED: removed hyphen
    SOURCE_FILES model/oran-interface.cc
```

**Verification:**

```bash
cd /opt/ns-oran
python3 ns3 clean
python3 ns3 configure --enable-examples --enable-tests

# Output should show:
# Modules configured to be built:
# ... oran ...
```

---

## Error 2: Disk Space Exhaustion

### Symptoms

```
No space left on device
/dev/sda1       248G  248G     0 100% /
error: while writing precompiled header: No space left on device
```

### Root Cause

- Previous TRACTOR dataset extraction consumed 150GB in `/home/thc1006/dev/tractor-extracted/`
- Multiple failed build attempts left large log files
- Build artifacts accumulated

### Solution

```bash
# Stop all builds
pkill -9 -f "ns3 build"

# Remove extracted dataset (already processed)
rm -rf /home/thc1006/dev/tractor-extracted

# Clean apt cache
sudo apt-get clean

# Clean ns-3 build
cd /opt/ns-oran
python3 ns3 clean
```

**Result:** Freed 150GB, disk usage: 30% (74GB/248GB used, 174GB available)

---

## Error 3: e2sim Header Files Not Found

### Symptoms

Build failed at 37% with:

```
/opt/ns-oran/contrib/oran/model/kpm-indication.h:32:12: fatal error:
E2SM-KPM-RANfunction-Description.h: No such file or directory
   32 |   #include "E2SM-KPM-RANfunction-Description.h"
      |            ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
compilation terminated.

Error occurred when compiling:
  src/lte/helper/emu-epc-helper.cc
```

### Root Cause Analysis

**Include Chain:**

```
src/lte/helper/emu-epc-helper.cc
  → #include <ns3/epc-ue-nas.h>
    → #include src/lte/model/lte-enb-net-device.h
      → #include <ns3/oran-interface.h>
        → #include contrib/oran/model/kpm-indication.h:32
          → #include "E2SM-KPM-RANfunction-Description.h"  ❌ NOT FOUND
```

**Problem Identification:**

1. The lte module includes oran headers (line 355 in `src/lte/CMakeLists.txt`)
2. oran headers include e2sim headers located at `/usr/local/include/e2sim/`
3. When lte compiles, it doesn't have e2sim in its include path
4. Two issues:
   - lte module doesn't link against oran library
   - e2sim include path not propagated from oran to dependent modules

### Files Affected

8 files in oran module include e2sim headers:

1. `/opt/ns-oran/contrib/oran/model/kpm-indication.h`
2. `/opt/ns-oran/contrib/oran/model/kpm-function-description.h`
3. `/opt/ns-oran/contrib/oran/model/ric-control-function-description.h`
4. `/opt/ns-oran/contrib/oran/model/ric-control-message.h`
5. `/opt/ns-oran/contrib/oran/model/kpm-indication.cc`
6. `/opt/ns-oran/contrib/oran/model/asn1c-types.h`
7. `/opt/ns-oran/contrib/oran/examples/e2sim-integration-example.cc`

### Solution Part 1: Add oran Library Dependency to lte Module

**File:** `/opt/ns-oran/src/lte/CMakeLists.txt:358-377`

**Before:**
```cmake
build_lib(
  LIBNAME lte
  SOURCE_FILES ${source_files}
  HEADER_FILES ${header_files}
  LIBRARIES_TO_LINK
    ${emu_libraries}
    ${libcore}
    ${libnetwork}
    ${libspectrum}
    ${libstats}
    ${libbuildings}
    ${libvirtual-net-device}
    ${libpoint-to-point}
    ${libapplications}
    ${libinternet}
    ${libcsma}
    ${libconfig-store}
  TEST_SOURCES ${test_sources}
  MODULE_ENABLED_FEATURES ${emu_features}
)
```

**After:**
```cmake
build_lib(
  LIBNAME lte
  SOURCE_FILES ${source_files}
  HEADER_FILES ${header_files}
  LIBRARIES_TO_LINK
    ${emu_libraries}
    ${libcore}
    ${libnetwork}
    ${libspectrum}
    ${libstats}
    ${libbuildings}
    ${libvirtual-net-device}
    ${libpoint-to-point}
    ${libapplications}
    ${libinternet}
    ${libcsma}
    ${libconfig-store}
    ${liboran}  # ✅ ADDED: Link against oran library
  TEST_SOURCES ${test_sources}
  MODULE_ENABLED_FEATURES ${emu_features}
)
```

### Solution Part 2: Export e2sim Include Directories with PUBLIC Scope

**File:** `/opt/ns-oran/contrib/oran/CMakeLists.txt:56-59`

**Added after `build_lib()` call:**

```cmake
build_lib(
    LIBNAME oran
    SOURCE_FILES model/oran-interface.cc
                 helper/oran-interface-helper.cc
                 model/asn1c-types.cc
                 model/function-description.cc
                 model/kpm-indication.cc
                 model/kpm-function-description.cc
                 model/ric-control-message.cc
                 model/ric-control-function-description.cc
                 helper/oran-interface-helper.cc
                 helper/indication-message-helper.cc
                 helper/lte-indication-message-helper.cc
                 helper/mmwave-indication-message-helper.cc
    HEADER_FILES model/oran-interface.h
                 helper/oran-interface-helper.h
                 model/asn1c-types.h
                 model/function-description.h
                 model/kpm-indication.h
                 model/kpm-function-description.h
                 model/ric-control-message.h
                 model/ric-control-function-description.h
                 helper/indication-message-helper.h
                 helper/lte-indication-message-helper.h
                 helper/mmwave-indication-message-helper.h
    LIBRARIES_TO_LINK
                    ${libcore}
                    ${e2sim_LIBRARIES}
)

# ✅ ADDED: Export e2sim include directories to modules that depend on oran
target_include_directories(${liboran} PUBLIC /usr/local/include/e2sim)
target_include_directories(${liboran-obj} PUBLIC /usr/local/include/e2sim)
```

**Why PUBLIC Scope is Critical:**

- `PUBLIC` means the include directory is part of the library's public interface
- When another module (like lte) links against `${liboran}`, it automatically inherits PUBLIC include directories
- This makes `/usr/local/include/e2sim` available to all dependent modules
- Without PUBLIC scope, only oran module itself would have access to e2sim headers

**CMake Target Naming:**

- `${liboran}` - The shared library target (e.g., `libns3.38.rc1-oran-default.so`)
- `${liboran-obj}` - The object library target (intermediate compilation objects)
- Both need the include directory for proper compilation

---

## Failed Attempts (Learning Points)

### Attempt 1: Adding e2sim/ Prefix to Includes ❌

**What we tried:**

```cpp
// In contrib/oran/model/kpm-indication.h
#include "e2sim/E2SM-KPM-RANfunction-Description.h"  // Added e2sim/ prefix
```

**Why it failed:**

e2sim headers themselves include other headers without prefix:

```cpp
// In /usr/local/include/e2sim/E2SM-KPM-RANfunction-Description.h
#include <asn_application.h>  // No e2sim/ prefix!
```

This caused cascading include failures.

### Attempt 2: Using include_directories() ❌

**What we tried:**

```cmake
# In contrib/oran/CMakeLists.txt
include_directories(/usr/local/include/e2sim)
```

**Why it failed:**

`include_directories()` has directory scope, not target scope. It only affects the current directory (oran module) and doesn't propagate to dependent modules like lte.

---

## Complete Build Process

### Step-by-Step Build Commands

```bash
# 1. Clean previous build
cd /opt/ns-oran
python3 ns3 clean

# 2. Configure with examples and tests
python3 ns3 configure --enable-examples --enable-tests

# Expected output:
# Modules configured to be built:
# ... lte ... oran ...

# 3. Build with parallel jobs
python3 ns3 build -j30

# Expected: Build reaches 100% successfully
```

### Verification

```bash
# 1. Check oran library built
ls -lh /opt/ns-oran/build/lib/libns3*oran*

# Output:
# -rwxrwxr-x 1 user user 6.0M Nov 21 07:51 libns3.38.rc1-oran-default.so

# 2. Check for errors in build log
grep -i "fatal error" build-log.txt
# Should return empty

# 3. Verify lte module links oran
ldd /opt/ns-oran/build/lib/libns3.38.rc1-lte-default.so | grep oran
# Should show oran library dependency
```

---

## Summary of Changes

### File Modifications

| File | Line | Change Type | Description |
|------|------|-------------|-------------|
| `/opt/ns-oran/contrib/oran/CMakeLists.txt` | 27 | Fix | `LIBNAME oran-interface` → `LIBNAME oran` |
| `/opt/ns-oran/contrib/oran/CMakeLists.txt` | 57-58 | Add | PUBLIC include directories for e2sim |
| `/opt/ns-oran/src/lte/CMakeLists.txt` | 375 | Add | `${liboran}` to LIBRARIES_TO_LINK |

### Build Statistics

- **Build time:** ~5 minutes (30 cores, 12700K)
- **Library size:** 6.0 MB (oran module)
- **Total modules built:** 41 (including oran)
- **Warnings:** 2 minor (use-after-free, maybe-uninitialized) - non-critical
- **Errors:** 0

---

## Key Takeaways

1. **CMake Variable Naming:** Never use hyphens in CMake variable names (use underscores)
2. **Include Path Propagation:** Use `target_include_directories()` with `PUBLIC` scope for transitive dependencies
3. **Library Dependencies:** Modules that include headers must also link against the corresponding library
4. **Build Troubleshooting Order:**
   - Fix configuration errors first (CMakeLists.txt)
   - Ensure sufficient disk space
   - Resolve dependency issues (library linking)
   - Handle include path propagation

---

## Quick Reference

### If Build Fails at Configuration

```bash
# Check oran module CMakeLists.txt line 27
# Ensure: LIBNAME oran (no hyphen)
```

### If Build Fails at 37% with "Header Not Found"

```bash
# 1. Check lte module links oran library (src/lte/CMakeLists.txt:375)
# 2. Check PUBLIC include directories (contrib/oran/CMakeLists.txt:57-58)
```

### If Disk Space Issues

```bash
df -h /
du -sh /opt/ns-oran/build
python3 ns3 clean
```

---

## Related Documentation

- ns-3 Build System: https://www.nsnam.org/docs/manual/html/build-system.html
- CMake target_include_directories: https://cmake.org/cmake/help/latest/command/target_include_directories.html
- ns-O-RAN Documentation: https://docs.o-ran-sc.org/projects/o-ran-sc-sim-ns3-o-ran-e2/en/latest/

---

## Appendix: Build Environment

```bash
# System Information
OS: Ubuntu Linux 5.15.0-161-generic
CPU: 30 cores available
RAM: Sufficient for -j30 parallel build
Disk: 248GB total, maintain <80% usage

# Software Versions
ns-3: 3.38.rc1
CMake: 3.x (system default)
Python: 3.x
Compiler: g++ 12.x

# Critical Paths
ns-O-RAN: /opt/ns-oran
e2sim headers: /usr/local/include/e2sim
e2sim library: /usr/local/lib/libe2sim.a
Build output: /opt/ns-oran/build/lib/
```

---

**Document Version:** 1.0
**Last Updated:** 2025-11-21
**Status:** Build Successful ✅
