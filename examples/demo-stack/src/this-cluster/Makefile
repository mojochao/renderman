# Setting SHELL to bash allows bash commands to be executed by recipes.
# Options are set to exit when a recipe line exits non-zero or a piped command fails.
SHELL = /usr/bin/env bash -o pipefail
.SHELLFLAGS = -ec

# Ensure the Python version meets the minimum version requirements.
MIN_PYTHON_VERSION_MINOR = 12
PYTHON_VERSION = $(shell python3 --version | awk '{print $$2}')
PYTHON_VERSION_MINOR = $(shell echo $(PYTHON_VERSION) | cut -d '.' -f 2)
ifneq ($(shell echo "$(PYTHON_VERSION_MINOR) < $(MIN_PYTHON_VERSION_MINOR)" | bc),0)
$(error Python version $(PYTHON_VERSION) is not supported. Please use Python 3.$(MIN_PYTHON_VERSION_MINOR) or higher.)
endif

# Use generated, git-ignored kubeconfig in this directory.
export KUBECONFIG = $(shell pwd)/kubeconfig

# Set environment name from current directory base name.
env = $(shell basename "$(CURDIR)")

# Set repository root directory.
ROOT_DIR = $(shell git rev-parse --show-toplevel)

# Set scripts directory.
SCRIPTS_DIR = $(ROOT_DIR)/scripts

# Set output directory.
OUTPUT_DIR = $(ROOT_DIR)/clusters/$(env)

# Set Python virtual environment.
VENV_DIR = $(ROOT_DIR)/.venv
PYTHON := $(VENV_DIR)/bin/python3

# Set renderer script
renderer_app = $(ROOT_DIR)/scripts/manifests-renderer

# Set renderer script --app option for a specific app, if provided.
ifdef app
renderer_app_option = "--app $(app)"
endif

# Set renderer '--debug' option if debug=true to enable verbose output of commands.
ifeq ($(debug),true)
renderer_debug_option := --debug
endif

##@ Info

# The help target prints out all targets with their descriptions organized
# beneath their categories. The categories are represented by '##@' and the
# target descriptions by '##'. The awk commands is responsible for reading the
# entire set of makefiles included in this invocation, looking for lines of the
# file as xyz: ## something, and then pretty-format the target and help. Then,
# if there's a line with ##@ something, that gets pretty-printed as a category.
#
# See https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters for more
# info on the usage of ANSI control characters for terminal formatting.
#
# See http://linuxcommand.org/lc3_adv_awk.php for more info on the awk command.

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: apps
apps: ## List names of all apps managed by this Makefile
	@yq eval '.releases[].name' helmfile.yaml

.PHONY: vars
vars: ## Show build variables used by this Makefile
	@echo "KUBECONFIG: $(KUBECONFIG)"
	@echo "PYTHON:     $(PYTHON)"
	@echo "OUTPUT_DIR: $(OUTPUT_DIR)"
	@echo "env:        $(env)"
	@echo "app:        $(app)"

##@ Toolchain

.PHONY: tools
tools: ## Install toolchain used by this Makefile
	@echo "Installing tools..."
	$(SCRIPTS_DIR)/install-toolchain

##@ Renderer

.PHONY: check
check: ## Check git repo state is not dirty and rendered manifests consistent with source artifacts (app=NAME)
	$(PYTHON) $(renderer_app) check $(renderer_app_option) $(renderer_debug_option)

.PHONY: preview
preview: ## Preview rendered manifests from source artifacts (app=NAME)
	$(PYTHON) $(renderer_app) preview $(renderer_app_option) $(renderer_debug_option)

.PHONY: update
update: ## Update rendered manifests from source artifacts (app=NAME)
	$(PYTHON) $(renderer_app) update $(renderer_app_option) $(renderer_debug_option)

##@ Kubeconfig

.PHONY: kubeconfig
kubeconfig: ## Update kubeconfig for cluster
	@echo "Updating kubeconfig..."
	aws eks update-kubeconfig --name $(cluster) --alias $(cluster)
