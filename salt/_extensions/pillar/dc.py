import salt.loader

def compound(tgt, minion_id=None):
    opts = {'grains': __grains__, 'id': minion_id}
    matcher = salt.loader.matchers(dict(__opts__, **opts))['compound_match.match']
    try:
        return matcher(tgt)
    except Exception:
        pass
    return False


def ext_pillar(minion_id, pillar, **mapping):
    return next(
        (
            {"dc": datacenter}
            for pat, datacenter in mapping.items()
            if compound(pat, minion_id)
        ),
        {},
    )
