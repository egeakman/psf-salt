import binascii
import os.path

import salt.minion

from salt._compat import string_types

import OpenSSL


def compound(tgt, minion_id=None):
    opts = {'grains': __grains__}
    if minion_id is not None:
        if not isinstance(minion_id, string_types):
            minion_id = str(minion_id)
        else:
            minion_id = __grains__['id']
    opts['id'] = minion_id
    matcher = salt.minion.Matcher(opts, __salt__)
    try:
        return matcher.compound_match(tgt)
    except Exception:
        pass
    return False


def _secure_open_write(filename, fmode):
    # We only want to write to this file, so open it in write only mode
    flags = os.O_WRONLY

    # os.O_CREAT | os.O_EXCL will fail if the file already exists, so we only
    #  will open *new* files.
    # We specify this because we want to ensure that the mode we pass is the
    # mode of the file.
    flags |= os.O_CREAT | os.O_EXCL

    # Do not follow symlinks to prevent someone from making a symlink that
    # we follow and insecurely open a cache file.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    # On Windows we'll mark this file as binary
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY

    # Before we open our file, we want to delete any existing file that is
    # there
    try:
        os.remove(filename)
    except (IOError, OSError):
        # The file must not exist already, so we can just skip ahead to opening
        pass

    # Open our file, the use of os.O_CREAT | os.O_EXCL will ensure that if a
    # race condition happens between the os.remove and this line, that an
    # error will be raised.
    fd = os.open(filename, flags, fmode)
    try:
        return os.fdopen(fd, "wb")
    except:
        # An error occurred wrapping our FD in a file object
        os.close(fd)
        raise


def _new_serial():
    return int(binascii.hexlify(os.urandom(20)), 16)


def ca_exists(cacert_path, ca_name):
    certp = '{0}/{1}/{2}_ca_cert.crt'.format(cacert_path, ca_name, ca_name)
    return os.path.exists(certp)


def create_ca(cacert_path, ca_name,
              bits=2048,
              days=365,
              CN="PSF Infrastructure CA",
              C="US",
              ST="NH",
              L="Wolfeboro",
              O="Python Software Foundation",
              OU="Infrastructure Team",
              emailAddress="infrastructure-staff@python.org",
              digest="sha256"):

    certp = '{0}/{1}/{2}_ca_cert.crt'.format(cacert_path, ca_name, ca_name)
    ca_keyp = '{0}/{1}/{2}_ca_cert.key'.format(cacert_path, ca_name, ca_name)

    if ca_exists(cacert_path, ca_name):  # TODO: Check Expiration
        return

    if not os.path.exists('{0}/{1}'.format(cacert_path, ca_name)):
        os.makedirs('{0}/{1}'.format(cacert_path, ca_name))

    if os.path.exists(certp):
        os.remove(certp)

    if os.path.exists(ca_keyp):
        os.remove(ca_keyp)

    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, bits)

    ca = OpenSSL.crypto.X509()
    ca.set_version(2)
    ca.set_serial_number(_new_serial())
    ca.get_subject().C = C
    ca.get_subject().ST = ST
    ca.get_subject().L = L
    ca.get_subject().O = O
    if OU:
        ca.get_subject().OU = OU
    ca.get_subject().CN = CN
    ca.get_subject().emailAddress = emailAddress

    ca.gmtime_adj_notBefore(0)
    ca.gmtime_adj_notAfter(int(days) * 24 * 60 * 60)
    ca.set_issuer(ca.get_subject())
    ca.set_pubkey(key)

    ca.add_extensions([
        OpenSSL.crypto.X509Extension('basicConstraints', True,
                                     'CA:TRUE, pathlen:0'),
        OpenSSL.crypto.X509Extension('keyUsage', True,
                                     'keyCertSign, cRLSign'),
        OpenSSL.crypto.X509Extension('subjectKeyIdentifier', False, 'hash',
                                     subject=ca)])

    ca.add_extensions([
        OpenSSL.crypto.X509Extension(
            'authorityKeyIdentifier',
            False,
            'issuer:always,keyid:always',
            issuer=ca)])
    ca.sign(key, digest)

    with _secure_open_write(ca_keyp, 0o0600) as fp:
        fp.write(
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
        )

    with _secure_open_write(certp, 0o0644) as fp:
        fp.write(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca)
        )


def get_ca_cert(cacert_path, ca_name):
    certp = '{0}/{1}/{2}_ca_cert.crt'.format(cacert_path, ca_name, ca_name)

    with open(certp, "r") as fp:
        cert = fp.read()

    return cert


def cert_exists(cacert_path, ca_name, CN):
    certp = '{0}/{1}/certs/{2}.crt'.format(cacert_path, ca_name, CN)
    keyp = '{0}/{1}/private/{2}.key'.format(cacert_path, ca_name, CN)
    return os.path.exists(certp) and os.path.exists(keyp)


def create_ca_signed_cert(cacert_path, ca_name,
                          bits=2048,
                          days=365,
                          CN="localhost",
                          C="US",
                          ST="NH",
                          L="Wolfeboro",
                          O="Python Software Foundation",
                          OU="Infrastructure Team",
                          emailAddress="infrastructure-staff@python.org",
                          digest="sha256"):
    certp = '{0}/{1}/certs/{2}.crt'.format(cacert_path, ca_name, CN)
    keyp = '{0}/{1}/private/{2}.key'.format(cacert_path, ca_name, CN)
    ca_certp = '{0}/{1}/{2}_ca_cert.crt'.format(cacert_path, ca_name, ca_name)
    ca_keyp = '{0}/{1}/{2}_ca_cert.key'.format(cacert_path, ca_name, ca_name)

    if cert_exists(cacert_path, ca_name, CN):  # TODO: Check Expiration
        return

    if not os.path.exists(os.path.dirname(certp)):
        os.makedirs(os.path.dirname(certp))

    if not os.path.exists(os.path.dirname(keyp)):
        os.makedirs(os.path.dirname(keyp))

    if os.path.exists(certp):
        os.remove(certp)

    if os.path.exists(keyp):
        os.remove(keyp)

    with open(ca_certp, "r") as fp:
        ca_cert = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM,
            fp.read(),
        )

    with open(ca_keyp, "r") as fp:
        ca_key = OpenSSL.crypto.load_privatekey(
            OpenSSL.crypto.FILETYPE_PEM,
            fp.read(),
        )

    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, bits)

    # create certificate
    cert = OpenSSL.crypto.X509()
    cert.set_version(2)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(int(days) * 24 * 60 * 60)
    cert.get_subject().C = C
    cert.get_subject().ST = ST
    cert.get_subject().L = L
    cert.get_subject().O = O
    if OU:
        cert.get_subject().OU = OU
    cert.get_subject().CN = CN
    cert.get_subject().emailAddress = emailAddress
    cert.set_serial_number(_new_serial())
    cert.set_issuer(ca_cert.get_subject())
    cert.set_pubkey(key)

    # Sign the certificate with the CA
    cert.sign(ca_key, digest)

    # Write out the private and public keys
    with _secure_open_write(keyp, 0o0600) as fp:
        fp.write(
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
        )

    with _secure_open_write(certp, 0o0644) as fp:
        fp.write(
            OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
        )


def get_ca_signed_cert(cacert_path, ca_name, CN):
    certp = '{0}/{1}/certs/{2}.crt'.format(cacert_path, ca_name, CN)
    keyp = '{0}/{1}/private/{2}.key'.format(cacert_path, ca_name, CN)

    with open(certp, "r") as fp:
        cert = fp.read()

    with open(keyp, "r") as fp:
        key = fp.read()

    return {"crt": cert, "key": key}


def ext_pillar(minion_id, pillar, base="/etc/ssl", name="PSFCA", ca_opts=None):
    if ca_opts is None:
        ca_opts = {}

    # Ensure we have a CA created.
    create_ca(base, name, **ca_opts)

    # Determine the certificates required by this minion
    all_certificates = set()
    for role, certificates in pillar.get("ca", {}).get("roles", {}).items():
        if compound(pillar.get("roles", {}).get(role, ""), minion_id):
            all_certificates |= set(certificates)

    # Create all of the certificates required by this minion
    for certificate in all_certificates:
        opts = ca_opts.copy()
        opts["CN"] = certificate
        create_ca_signed_cert(base, name, **opts)

    # Get all of the certificates required by this minion
    data = {}
    for certificate in all_certificates:
        data[certificate] = get_ca_signed_cert(base, name, certificate)

    data[name] = {"crt": get_ca_cert(base, name)}

    return {
        "ca": {
            "certificates": data,
        },
    }
