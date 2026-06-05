SERVICES := incident-api triage-agent rca-agent remediation-agent notification-agent postmortem-agent

.PHONY: push-all build-all test-all lint-all $(SERVICES)

# Build and push a single service: make push SERVICE=triage-agent
push:
	$(MAKE) -C services/$(SERVICE) push

build:
	$(MAKE) -C services/$(SERVICE) build

test:
	$(MAKE) -C services/$(SERVICE) test

lint:
	$(MAKE) -C services/$(SERVICE) lint

run:
	$(MAKE) -C services/$(SERVICE) run

# Operate across all services
push-all:
	@for svc in $(SERVICES); do \
		echo "==> Pushing $$svc"; \
		$(MAKE) -C services/$$svc push; \
	done

build-all:
	@for svc in $(SERVICES); do \
		echo "==> Building $$svc"; \
		$(MAKE) -C services/$$svc build; \
	done

test-all:
	@for svc in $(SERVICES); do \
		echo "==> Testing $$svc"; \
		$(MAKE) -C services/$$svc test; \
	done

lint-all:
	@for svc in $(SERVICES); do \
		echo "==> Linting $$svc"; \
		$(MAKE) -C services/$$svc lint; \
	done
