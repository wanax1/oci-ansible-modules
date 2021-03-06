# Copyright (c) 2019 Oracle and/or its affiliates.
# This software is made available to you under the terms of the GPL 3.0 license or the Apache 2.0 license.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
# Apache License v2.0
# See LICENSE.TXT for details.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.oracle import oci_common_utils

try:
    import oci
    from oci.util import to_dict

    HAS_OCI_PY_SDK = True
except ImportError:
    HAS_OCI_PY_SDK = False

LIFECYCLE_STATE_WAITER_KEY = "LIFECYCLE_STATE_WAITER"
WORK_REQUEST_WAITER_KEY = "WORK_REQUEST_WAITER"
NONE_WAITER_KEY = "NONE_WAITER_KEY"


class Waiter:
    """Interface defining wait method"""

    def wait(self):
        raise NotImplementedError(
            "Expected to be implemented by the specific waiter classes."
        )


class BaseWaiter(Waiter):
    """Base class for various waiters"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        self.client = client
        self.operation_response = operation_response
        self.wait_for_states = wait_for_states
        self.resource_helper = resource_helper

    def get_initial_response(self):
        raise NotImplementedError(
            "Expected to be implemented by the specific waiter classes."
        )

    def get_evaluate_response_lambda(self):
        raise NotImplementedError(
            "Expected to be implemented by the specific waiter classes."
        )

    def wait(self):
        if not self.resource_helper.module.params.get("wait"):
            return self.operation_response
        wait_response = oci.wait_until(
            self.client,
            self.get_initial_response(),
            evaluate_response=self.get_evaluate_response_lambda(),
            max_wait_seconds=self.resource_helper.module.params.get(
                "wait_timeout", oci_common_utils.MAX_WAIT_TIMEOUT_IN_SECONDS
            ),
        )
        return self.get_resource_from_wait_response(wait_response)

    def get_resource_from_wait_response(self, wait_response):
        raise NotImplementedError(
            "Expected to be implemented by the specific waiter classes."
        )


class LifecycleStateWaiterBase(BaseWaiter):
    """Base class for various waiters"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        self.client = client
        self.operation_response = operation_response
        self.wait_for_states = wait_for_states
        self.resource_helper = resource_helper

    def get_initial_response(self):
        return self.resource_helper.get_resource()

    def get_evaluate_response_lambda(self):
        lowered_wait_for_states = [state.lower() for state in self.wait_for_states]
        return (
            lambda r: getattr(r.data, "lifecycle_state")
            and getattr(r.data, "lifecycle_state").lower() in lowered_wait_for_states
        )

    def get_resource_from_wait_response(self, wait_response):
        return wait_response.data


class LifecycleStateWaiter(LifecycleStateWaiterBase):
    """Waiter which waits on the lifecycle state of the resource"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        super(LifecycleStateWaiter, self).__init__(
            client, resource_helper, operation_response, wait_for_states
        )


class CreateOperationLifecycleStateWaiter(LifecycleStateWaiterBase):
    """Waiter which waits on the lifecycle state of the resource"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        super(CreateOperationLifecycleStateWaiter, self).__init__(
            client, resource_helper, operation_response, wait_for_states
        )

    def get_initial_response(self):
        identifier = self.operation_response.data.id
        if not identifier:
            self.resource_helper.module.fail_json(
                "Error getting the resource identifier."
            )
        try:
            id_orig = self.resource_helper.module.params[
                self.resource_helper.get_module_resource_id_param()
            ]
        except NotImplementedError:
            return self.resource_helper.get_resource()
        self.resource_helper.module.params[
            self.resource_helper.get_module_resource_id_param()
        ] = identifier
        get_response = self.resource_helper.get_resource()
        self.resource_helper.module.params[
            self.resource_helper.get_module_resource_id_param()
        ] = id_orig
        return get_response


class WorkRequestWaiter(BaseWaiter):
    """Waiter which waits on the work request"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        self.client = client
        self.resource_helper = resource_helper
        self.operation_response = operation_response
        self.wait_for_states = wait_for_states

    def get_initial_response(self):
        return self.client.get_work_request(
            self.operation_response.headers["opc-work-request-id"]
        )

    def get_evaluate_response_lambda(self):
        lowered_wait_for_states = [state.lower() for state in self.wait_for_states]
        return (
            lambda r: getattr(r.data, "status")
            and getattr(r.data, "status").lower() in lowered_wait_for_states
        )

    def get_resource_from_wait_response(self, wait_response):
        get_response = self.resource_helper.get_resource()
        return get_response.data


class CreateOperationWorkRequestWaiter(WorkRequestWaiter):
    """Waiter which waits on the work request"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        super(CreateOperationWorkRequestWaiter, self).__init__(
            client, resource_helper, operation_response, wait_for_states
        )

    def get_resource_from_wait_response(self, wait_response):
        entity_type = oci_common_utils.get_entity_type(
            self.resource_helper.resource_type
        )
        identifier = None
        for resource in wait_response.data.resources:
            if (
                hasattr(resource, "entity_type")
                and getattr(resource, "entity_type") == entity_type
            ):
                identifier = resource.identifier
        if not identifier:
            self.resource_helper.module.fail_json(
                msg="Could not get the resource identifier from work request response {0}".format(
                    to_dict(wait_response.data)
                )
            )
        get_response = self.resource_helper.get_get_fn()(identifier)
        return get_response.data


class NoneWaiter(Waiter):
    """Waiter which does not wait"""

    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        self.client = client
        self.resource_helper = resource_helper
        self.operation_response = operation_response
        self.wait_for_states = wait_for_states

    def wait(self):
        return self.operation_response.data


class AuditConfigurationLifecycleStateWaiter(LifecycleStateWaiter):
    def __init__(self, client, resource_helper, operation_response, wait_for_states):
        super(AuditConfigurationLifecycleStateWaiter, self).__init__(
            client, resource_helper, operation_response, wait_for_states
        )

    def get_evaluate_response_lambda(self):
        # The update operation currently returns a work request id but the AuditClient currently does not support
        # waiting for the work request. So wait until the configuration is updated by checking the value.
        return (
            lambda r: r.data.retention_period_days
            == self.resource_helper.module.params.get("retention_period_days")
        )


# A map specifying the overrides for the default waiters.
# Key is a tuple consisting spec name, resource type and the operation and the value is the waiter class.
# For ex: ("waas", "waas_policy", oci_common_utils.UPDATE_OPERATION_KEY) -> CustomWaasWaiterClass
_WAITER_OVERRIDE_MAP = {
    # The audit update operation currently returns a work request id but the AuditClient currently does not support
    # waiting for the work request. So inject NoneWaiter and customize it to manually wait on the update condition.
    ("audit", "configuration", oci_common_utils.UPDATE_OPERATION_KEY): NoneWaiter
}


def get_waiter_override(namespace, resource_type, operation):
    """Return the custom waiter class if any for the resource and operation. Else return None."""
    waiter_override_key = (namespace, resource_type, operation)
    if waiter_override_key in _WAITER_OVERRIDE_MAP:
        return _WAITER_OVERRIDE_MAP.get(waiter_override_key)
    # check if an override exists for ANY_OPERATION_KEY. This is helpful if we need a custom waiter for all(any)
    # resource operations
    waiter_override_key = (namespace, resource_type, oci_common_utils.ANY_OPERATION_KEY)
    if waiter_override_key in _WAITER_OVERRIDE_MAP:
        return _WAITER_OVERRIDE_MAP.get(waiter_override_key)
    return None


def get_waiter(
    waiter_type, operation, client, resource_helper, operation_response, wait_for_states
):
    """Return appropriate waiter object based on type and the operation."""
    # First check if there is any custom override for the waiter class. If exists, use it.
    waiter_override_class = get_waiter_override(
        resource_helper.namespace, resource_helper.resource_type, operation
    )
    if waiter_override_class:
        return waiter_override_class(
            client, resource_helper, operation_response, wait_for_states
        )
    if waiter_type == LIFECYCLE_STATE_WAITER_KEY:
        if operation == oci_common_utils.CREATE_OPERATION_KEY:
            return CreateOperationLifecycleStateWaiter(
                client, resource_helper, operation_response, wait_for_states
            )
        return LifecycleStateWaiter(
            client, resource_helper, operation_response, wait_for_states
        )
    elif waiter_type == WORK_REQUEST_WAITER_KEY:
        if operation == oci_common_utils.CREATE_OPERATION_KEY:
            return CreateOperationWorkRequestWaiter(
                client, resource_helper, operation_response, wait_for_states
            )
        return WorkRequestWaiter(
            client, resource_helper, operation_response, wait_for_states
        )
    return NoneWaiter(client, resource_helper, operation_response, wait_for_states)


def call_and_wait(
    call_fn,
    call_fn_args,
    call_fn_kwargs,
    waiter_type,
    operation,
    waiter_client,
    resource_helper,
    wait_for_states,
):
    """Call the given function and wait until the operation is completed and return the resource."""
    operation_response = oci_common_utils.call_with_backoff(
        call_fn, *call_fn_args, **call_fn_kwargs
    )
    waiter = get_waiter(
        waiter_type,
        operation,
        waiter_client,
        resource_helper,
        operation_response=operation_response,
        wait_for_states=wait_for_states,
    )
    return waiter.wait()
