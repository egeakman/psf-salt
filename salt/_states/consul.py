def external_service(name, datacenter, node, address, port, token=None):
    ret = {'name': name, 'changes': {}, 'result': False, 'comment': ''}

    if token is None:
        token = __pillar__['consul']['acl']['tokens']['default']

    # Determine if the cluster is ready
    if not __salt__["consul.cluster_ready"]():
        ret["result"] = True
        ret["comment"] = "Consul cluster is not ready."
        return ret

    # Determine if the node we're attempting to register exists
    if __salt__["consul.node_exists"](
        node, address, dc=datacenter
    ) and __salt__["consul.node_service_exists"](
        node, name, port, dc=datacenter
    ):
        ret["result"] = True
        ret["comment"] = f"External Service {name} already in the desired state."
        return ret

    if __opts__['test'] == True:
        ret['comment'] = 'The state of "{0}" will be changed.'.format(name)
        ret['changes'] = {'old': None, 'new': f'External Service {name}'}
        ret["result"] = None
        return ret

    __salt__["consul.register_external_service"](
        node, address, datacenter, name, port, token,
    )

    ret["result"] = True
    ret["comment"] = f"Registered external service: '{name}'."
    ret["changes"] = {"old": None, "new": f'External Service {name}'}

    return ret
