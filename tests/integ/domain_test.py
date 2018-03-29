##############################################################################
# Copyright by The HDF Group.                                                #
# All rights reserved.                                                       #
#                                                                            #
# This file is part of HSDS (HDF5 Scalable Data Service), Libraries and      #
# Utilities.  The full HSDS copyright notice, including                      #
# terms governing use, modification, and redistribution, is contained in     #
# the file COPYING, which can be found at the root of the source code        #
# distribution tree.  If you do not have access to this file, you may        #
# request a copy from help@hdfgroup.org.                                     #
##############################################################################
import unittest
import warnings
import requests
import time
import json
import config
import helper

# ----------------------------------------------------------------------

class GetDomainPatternsTest(unittest.TestCase):

    def assertLooksLikeUUID(self, s):
        self.assertTrue(helper.validateId(s))

    def __init__(self, *args, **kwargs):
        super(GetDomainPatternsTest, self).__init__(*args, **kwargs)
        self.base_domain = helper.getTestDomainName(self.__class__.__name__)
        helper.setupDomain(self.base_domain)

        self.endpoint = helper.getEndpoint()
        self.headers = helper.getRequestHeaders()

        response = requests.get(
                self.endpoint + "/",
                headers = helper.getRequestHeaders(domain=self.base_domain))
        assert response.status_code == 200, f"HTTP code {response.status_code}"
        self.expected_root = response.json()["root"]

    # this is what we did to get our expected root
    def testHeaderHost(self):
        # domain is recorded as 'host' header
        headers_with_host = helper.getRequestHeaders(domain=self.base_domain)
        response = requests.get(
                self.endpoint + "/",
                headers=headers_with_host)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json()["root"], self.expected_root)

    def testHeaderHostMissingLeadSlash(self):
        bad_domain = self.base_domain[1:] # remove leading '/'
        headers = helper.getRequestHeaders(domain=bad_domain)
        response = requests.get(self.endpoint + "/", headers=headers)
        self.assertEqual(response.status_code, 400)

    def testQueryHost(self):
        params = {"host": self.base_domain}
        response = requests.get(
                self.endpoint + "/",
                headers=self.headers,
                params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json()["root"], self.expected_root)

    def testQueryHostMissingLeadSlash(self):
        params = {"host": self.base_domain[1:]} # remove leading '/'
        response = requests.get(
                self.endpoint + "/",
                headers=self.headers)
        self.assertEqual(response.status_code, 400)

    def testQueryHostDNS(self):
        dns_domain = helper.getDNSDomain(self.base_domain)
        response = requests.get(
                self.endpoint + "/",
                headers=self.headers,
                params={"host": dns_domain})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json()["root"], self.expected_root)

    def testQueryHostDNSMalformed(self):
        dns_domain = helper.getDNSDomain(self.base_domain)
        req = self.endpoint + "/"

        for predomain in (
            "two.dots..are.bad.",
            "no/slash",
            ".",
            ".sure.leading.dot",
        ):
            domain = predomain + dns_domain
            response = requests.get(
                    req,
                    headers=self.headers,
                    params={"host": domain})
            self.assertEqual(
                    response.status_code,
                    400,
                    f"predomain '{predomain}' should fail")

    def testHeaderHostDNS(self):
        dns_domain = helper.getDNSDomain(self.base_domain)
        req = helper.getEndpoint() + '/'

        # verify we can access base domain as via dns name
        headers = helper.getRequestHeaders(domain=dns_domain)
        response = requests.get(req, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertLooksLikeUUID(response.json()["root"])

    def testHeaderHostDNSMalformed(self):
        dns_domain = helper.getDNSDomain(self.base_domain)
        req = helper.getEndpoint() + '/'

        for predomain in (
            "two.dots..are.bad.",
            "no/slash",
            ".",
            ".sure.leading.dot",
        ):
            domain = predomain + dns_domain
            headers = helper.getRequestHeaders(domain=domain)
            response = requests.get(req, headers=headers)
            self.assertEqual(
                    response.status_code,
                    400,
                    f"predomain '{predomain}' should fail")

    def testQueryDomain(self):
        params = {"domain": self.base_domain}
        response = requests.get(
                self.endpoint + "/",
                headers=self.headers,
                params=params)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'application/json')
        self.assertEqual(response.json()["root"], self.expected_root)

    def testQueryDomainMissingLeadSlash(self):
        params = {"domain": self.base_domain[1:]} # remove leading '/'
        response = requests.get(
                self.endpoint + "/",
                headers=self.headers)
        self.assertEqual(response.status_code, 400)

# ----------------------------------------------------------------------

@unittest.skipUnless(
        config.get("test_on_uploaded_file"),
        "sample file may not be present")
class OperationsOnUploadedTest(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(OperationsOnUploadedTest, self).__init__(*args, **kwargs)
        self.base_domain = helper.getTestDomainName(self.__class__.__name__)
        helper.setupDomain(self.base_domain)

    def testGetDomain(self):
        domain = helper.getTestDomain("tall.h5")
        headers = helper.getRequestHeaders(domain=domain)

        req = helper.getEndpoint() + '/'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(
                rsp.status_code, 200, f"Failed to get domain {self.domain}")
        self.assertEqual(rsp.headers['content-type'], 'application/json')
        rspJson = rsp.json()

        now = time.time()
        self.assertTrue(rspJson["created"] < now - 60 * 5)
        self.assertTrue(rspJson["lastModified"] < now - 60 * 5)
        self.assertEqual(len(rspJson["hrefs"]), 7)
        self.assertTrue(rspJson["root"].startswith("g-"))
        self.assertTrue(rspJson["owner"])
        self.assertEqual(rspJson["class"], "domain")
        self.assertFalse(
                "num_groups" in rspJson,
                "'num_groups' should only show up with the verbose param")
        self.assertLooksLikeUUID(rspJson["root"])

    def testGetByPath(self):
        domain = helper.getTestDomain("tall.h5")
        headers = helper.getRequestHeaders(domain=domain)

        req = helper.getEndpoint() + '/'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(
                rsp.status_code, 200, f"Failed to get domain {self.domain}")
        domainJson = json.loads(rsp.text)
        self.assertTrue("root" in domainJson)
        root_id = domainJson["root"]

        # Get group at /g1/g1.1 by using h5path
        params = {"h5path": "/g1/g1.1"}
        rsp = requests.get(req, headers=headers, params=params)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("id" in rspJson)
        g11id = helper.getUUIDByPath(domain, "/g1/g1.1")
        self.assertEqual(g11id, rspJson["id"])
        self.assertTrue("root" in rspJson)
        self.assertEqual(root_id, rspJson["root"])

        # Get dataset at /g1/g1.1/dset1.1.1 by using relative h5path
        params = {"h5path": "./g1/g1.1/dset1.1.1"}
        rsp = requests.get(req, headers=headers, params=params)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("id" in rspJson)
        d111id = helper.getUUIDByPath(domain, "/g1/g1.1/dset1.1.1")
        self.assertEqual(d111id, rspJson["id"])
        self.assertTrue("root" in rspJson)
        self.assertEqual(root_id, rspJson["root"])

    def testDomainCollections(self):
        domain = helper.getTestDomain("tall.h5")
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200, f"Can't get domain: {domain}")

        rspJson = json.loads(rsp.text)
        for k in ("root", "owner", "created", "lastModified"):
             self.assertTrue(k in rspJson)

        root_id = rspJson["root"]
        self.assertLooksLikeUUID(root_id)

        # get the datasets collection
        req = helper.getEndpoint() + '/datasets'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("datasets" in rspJson)
        datasets = rspJson["datasets"]
        for objid in datasets:
            self.assertLooksLikeUUID(objid)
        self.assertEqual(len(datasets), 4)

        # get the first 2 datasets
        params = {"Limit": 2}
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("datasets" in rspJson)
        batch = rspJson["datasets"]
        self.assertEqual(len(batch), 2)
        self.assertLooksLikeUUID(batch[0])
        self.assertEqual(batch[0], datasets[0])
        self.assertLooksLikeUUID(batch[1])
        self.assertEqual(batch[1], datasets[1])
        # next batch
        params["Marker"] = batch[1]
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("datasets" in rspJson)
        batch = rspJson["datasets"]
        self.assertEqual(len(batch), 2)
        self.assertLooksLikeUUID(batch[0])
        self.assertEqual(batch[0], datasets[2])
        self.assertLooksLikeUUID(batch[1])
        self.assertEqual(batch[1], datasets[3])

        # get the groups collection
        req = helper.getEndpoint() + '/groups'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("groups" in rspJson)
        groups = rspJson["groups"]
        self.assertEqual(len(groups), 5)
        # get the first 2 groups
        params = {"Limit": 2}
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("groups" in rspJson)
        batch = rspJson["groups"]
        self.assertEqual(len(batch), 2)
        self.assertLooksLikeUUID(batch[0])
        self.assertEqual(batch[0], groups[0])
        self.assertLooksLikeUUID(batch[1])
        self.assertEqual(batch[1], groups[1])
        # next batch
        params["Marker"] = batch[1]
        params["Limit"] = 100
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("groups" in rspJson)
        batch = rspJson["groups"]
        self.assertEqual(len(batch), 3)
        for i in range(3):
            self.assertLooksLikeUUID(batch[i])
            self.assertEqual(batch[i], groups[2+i])

        # get the datatypes collection
        req = helper.getEndpoint() + '/datatypes'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)
        self.assertTrue("datatypes" in rspJson)
        datatypes = rspJson["datatypes"]
        self.assertEqual(len(datatypes), 0)  # no datatypes in this domain

    def testGetDomainVerbose(self):
        domain = helper.getTestDomain("tall.h5")
        headers = helper.getRequestHeaders(domain=domain)

        req = helper.getEndpoint() + '/'
        params = {"verbose": 1}
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200, f"Can't get domain: {domain}")

        self.assertEqual(rsp.headers['content-type'], 'application/json')
        rspJson = json.loads(rsp.text)

        for name in ("lastModified", "created", "hrefs", "root", "owner", "class"):
            self.assertTrue(name in rspJson)
        now = time.time()
        self.assertTrue(rspJson["created"] < now - 60 * 5)
        self.assertTrue(rspJson["lastModified"] < now - 60 * 5)
        self.assertEqual(len(rspJson["hrefs"]), 7)
        self.assertTrue(rspJson["root"].startswith("g-"))
        self.assertTrue(rspJson["owner"])
        self.assertEqual(rspJson["class"], "domain")

        root_uuid = rspJson["root"]
        self.assertLooksLikeUUID(root_uuid)

        self.assertTrue("num_groups" in rspJson)
        self.assertEqual(rspJson["num_groups"], 5)
        self.assertTrue("num_datasets" in rspJson)
        self.assertEqual(rspJson["num_datasets"], 4)
        self.assertTrue("num_datatypes" in rspJson)
        self.assertEqual(rspJson["num_datatypes"], 0)
        self.assertTrue("allocated_bytes" in rspJson)

        # test that allocated_bytes falls in a given range
        self.assertTrue(rspJson["allocated_bytes"] > 5000)
        self.assertTrue(rspJson["allocated_bytes"] < 6000)
        self.assertTrue("num_chunks" in rspJson)
        self.assertTrue(rspJson["num_chunks"], 4)

# ----------------------------------------------------------------------

class DomainTest(unittest.TestCase):

    def assertLooksLikeUUID(self, s):
        self.assertTrue(helper.validateId(s))

    def assertDictHasOnlyTheseKeys(self, keys, d):
        for key in keys :
            self.assertTrue(key in d, "missing element: {key}")
        self.assertEqual(
                len(keys),
                len(d),
                list(d.keys()))

    def assertLooksLikePutFolderResult(self, _json):
        putfolder_keys = (
            "owner",
            "acls",
            "created",
            "lastModified",
        )
        self.assertDictHasOnlyTheseKeys(putfolder_keys, _json)

    def assertLooksLikeGetFolderResult(self, _json):
        getfolder_keys = (
            "owner",
            "hrefs",
            "created",
            "class",
            "lastModified",
        )
        self.assertDictHasOnlyTheseKeys(getfolder_keys, _json)
        self.assertEqual(_json["class"], "folder")

    def assertLooksLikePutDomainResult(self, _json):
        putdomain_keys = (
            "root",
            "owner",
            "acls",
            "created",
            "lastModified",
        )
        self.assertDictHasOnlyTheseKeys(putdomain_keys, _json)
        self.assertLooksLikeUUID(_json["root"])

    def assertLooksLikeGetDomainResult(self, _json):
        getdomain_keys = (
            "root",
            "owner",
            "created",
            "lastModified",
            "class",
            "hrefs",
        )
        self.assertDictHasOnlyTheseKeys(getdomain_keys, _json)
        self.assertEqual(_json["class"], "domain")
        self.assertLooksLikeUUID(_json["root"])

    def __init__(self, *args, **kwargs):
        super(DomainTest, self).__init__(*args, **kwargs)
        self.base_domain = helper.getTestDomainName(self.__class__.__name__)
        helper.setupDomain(self.base_domain)

    def testGetFolderDomains(self):
        req = helper.getEndpoint() + "/"
        username = config.get("user_name")
        for domain in ( # demonstrate both path- and dns-like domain names
            "/home",
            "home",
            f"/home/{username}",
            f"{username}.home",
        ):
            headers = helper.getRequestHeaders(domain=domain)
            response = requests.get(req, headers=headers)
            self.assertEqual(
                    response.status_code,
                    200,
                    f"Unable to get domain {domain}")
            self.assertLooksLikeGetFolderResult(response.json())

    def testCreateAndGetDomain(self):
        domain = self.base_domain + "/newdomain.h6"
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        # must not already exist
        get_absent_code = requests.get(req, headers=headers).status_code
        self.assertEqual(get_absent_code, 404)

        # put up new Domain
        rsp = requests.put(req, headers=headers)
        self.assertEqual(rsp.status_code, 201)

        # verify expected elements returned
        rspJson = rsp.json()
        self.assertLooksLikePutDomainResult(rspJson)
        root_id = rspJson["root"]

        # putting the same domain again fails with a 409 error
        self.assertEqual(requests.put(req, headers=headers).status_code, 409)

        # verify that we can get the Domain back
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        self.assertLooksLikeGetDomainResult(rsp.json())

    def testCreateDomainNotAuthorizedFails401(self):
        domain = self.base_domain + "/user_infringement.h6"
        headers = helper.getRequestHeaders(domain=domain)
        other_user = "user2" if config.get("user_name") != "user2" else "user3"
        other_headers = helper.getRequestHeaders(
                domain=domain,
                username=other_user)
        req = helper.getEndpoint() + '/'

        # domain must not already exist
        get_absent_code = requests.get(req, headers=headers).status_code
        self.assertEqual(get_absent_code, 404)

        # other user lacks permission to create domain
        other_put_code = requests.put(req, headers=other_headers).status_code
        self.assertEqual(other_put_code, 401)

    def testCreateAndGetFolder(self):
        domain = self.base_domain + "/newfolder"
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        # must not already exist
        get_absent_code = requests.get(req, headers=headers).status_code
        self.assertEqual(get_absent_code, 404)

        # put up new Domain
        body = {"folder": True}
        rsp = requests.put(req, headers=headers, data=json.dumps(body))
        self.assertEqual(rsp.status_code, 201)

        # verify expected elements returned
        rspJson = rsp.json()
        self.assertLooksLikePutFolderResult(rspJson)

        # verify that putting the same folder again fails with a 409 error
        rsp = requests.put(req, data=json.dumps(body), headers=headers)
        self.assertEqual(rsp.status_code, 409)

        # verify that putting a domain with the same name also 409s
        rsp = requests.put(req, headers=headers)
        self.assertEqual(rsp.status_code, 409)

        # get newly-created folder and inspect
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = rsp.json()
        self.assertLooksLikeGetFolderResult(rspJson)

    def testCreateDomainInMissingFolderFails404(self):
        domain = self.base_domain + "/notafolder/newdomain.h5"
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        rsp = requests.put(req, headers=headers)
        self.assertEqual(rsp.status_code, 404)

    def testGetMissingDomainFails404(self):
        domain =  self.base_domain + "/doesnotexist.h6"
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 404)

    # TODO: if this fails, there may be a lingering "deleteme.h6" domain
    def testDeleteDomain(self):
        domain = self.base_domain + "/deleteme.h6"
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        # domain does not exist
        self.assertEqual(requests.get(req, headers=headers).status_code, 404)

        # create domain
        self.assertEqual(requests.put(req, headers=headers).status_code, 201)

        # can get domain
        self.assertEqual(requests.get(req, headers=headers).status_code, 200)

        # user without permission cannot delete domain
        other_headers = helper.getRequestHeaders(
                domain=self.base_domain,
                username="test_user2")
        self.assertEqual(
                requests.delete(req, headers=other_headers).status_code,
                403)

        # delete the domain with the orginal user
        self.assertEqual(
                requests.delete(req, headers=headers).status_code,
                200)

        # cannot get deleted Domain
        self.assertEqual(requests.get(req, headers=headers).status_code, 410)

    # TODO: if this fails, there may be a lingering "deleteme.h6" domain
    def testReplaceDeletedDomain(self):
        domain = self.base_domain + "/deleteme.h6"
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/'

        # SETUP: create domain
        self.assertEqual(requests.put(req, headers=headers).status_code, 201)

        # SETUP: delete the domain
        self.assertEqual(
                requests.delete(req, headers=headers).status_code,
                200)

        # TEST: can create new domain with same name
        self.assertEqual(requests.put(req, headers=headers).status_code, 201)

        # CLEANUP: remove domain again
        self.assertEqual(
                requests.delete(req, headers=headers).status_code,
                200)

    # TBD - try deleting a top-level domain

    # TBD - try deleting a domain that has child-domains

    # TODO: refactor the snot out of this
    def testNewDomainCollections(self):
        # verify that newly added groups/datasets show up in the collections
        headers = helper.getRequestHeaders(domain=self.base_domain)

        # get root id
        req = helper.getEndpoint() + '/'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        root_uuid = rspJson["root"]
        self.assertLooksLikeUUID(root_uuid)

        def make_group(parent_id, name):
            # create new group
            payload = { 'link': { 'id': parent_id, 'name': name } }
            req = helper.getEndpoint() + "/groups"
            rsp = requests.post(req, data=json.dumps(payload), headers=headers)
            self.assertEqual(rsp.status_code, 201)
            rspJson = json.loads(rsp.text)
            new_group_id = rspJson["id"]
            self.assertLooksLikeUUID(rspJson["id"])
            return new_group_id

        def make_dset(parent_id, name):
            type_vstr = {"charSet": "H5T_CSET_ASCII",
                "class": "H5T_STRING",
                "strPad": "H5T_STR_NULLTERM",
                "length": "H5T_VARIABLE" }
            payload = {'type': type_vstr, 'shape': 10,
                'link': {'id': parent_id, 'name': name} }
            req = helper.getEndpoint() + "/datasets"
            rsp = requests.post(req, data=json.dumps(payload), headers=headers)
            self.assertEqual(rsp.status_code, 201)  # create dataset
            rspJson = json.loads(rsp.text)
            dset_id = rspJson["id"]
            self.assertLooksLikeUUID(dset_id)
            return dset_id

        def make_ctype(parent_id, name):
            payload = {
                'type': 'H5T_IEEE_F64LE',
                'link': {'id': parent_id, 'name': name}
            }
            req = helper.getEndpoint() + "/datatypes"
            rsp = requests.post(req, data=json.dumps(payload), headers=headers)
            self.assertEqual(rsp.status_code, 201)
            rspJson = json.loads(rsp.text)
            dtype_id = rspJson["id"]
            self.assertLooksLikeUUID(dtype_id)
            return dtype_id

        group_ids = []
        group_ids.append(make_group(root_uuid, "g1"))
        group_ids.append(make_group(root_uuid, "g2"))
        group_ids.append(make_group(root_uuid, "g3"))
        g3_id = group_ids[2]
        dset_ids = []
        dset_ids.append(make_dset(g3_id, "ds1"))
        dset_ids.append(make_dset(g3_id, "ds2"))
        ctype_ids = []
        ctype_ids.append(make_ctype(g3_id, "ctype1"))

        # get the groups collection
        req = helper.getEndpoint() + '/groups'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)

        groups = rspJson["groups"]
        self.assertEqual(len(groups), len(group_ids))
        for objid in groups:
            self.assertLooksLikeUUID(objid)
            self.assertTrue(objid in group_ids)

        # get the datasets collection
        req = helper.getEndpoint() + '/datasets'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)

        datasets = rspJson["datasets"]
        self.assertEqual(len(datasets), len(dset_ids))
        for objid in datasets:
            self.assertLooksLikeUUID(objid)
            self.assertTrue(objid in dset_ids)

         # get the datatypes collection
        req = helper.getEndpoint() + '/datatypes'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("hrefs" in rspJson)

        datatypes = rspJson["datatypes"]
        self.assertEqual(len(datatypes), len(ctype_ids))
        for objid in datatypes:
            self.assertLooksLikeUUID(objid)
            self.assertTrue(objid in ctype_ids)

    def testGetDomains(self):
        import os.path as op
        # back up two levels
        domain = op.dirname(self.base_domain)
        domain = op.dirname(domain) + '/'
        headers = helper.getRequestHeaders(domain=domain)
        req = helper.getEndpoint() + '/domains'
        rsp = requests.get(req, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        self.assertEqual(rsp.headers['content-type'], 'application/json')
        rspJson = json.loads(rsp.text)
        self.assertTrue("domains" in rspJson)
        domains = rspJson["domains"]

        domain_count = len(domains)
        if domain_count < 9:
            # this should only happen in the very first test run
            # TODO: ^ what?
            warnings.warn(f"Expected to find more domains in {domain}")
            return

        for item in domains:
            name = item["name"]
            self.assertTrue(name.startsWith('/'))
            self.assertFalse(name.endsWith('/'))
            self.assertTrue("owner" in item)
            self.assertTrue("created" in item)
            self.assertTrue("lastModified" in item)
            self.assertTrue(item["class"] in ("domain", "folder"))

        # try getting the first 4 domains
        params = {"domain": domain, "Limit": 4}
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("domains" in rspJson)
        part1 = rspJson["domains"]

        self.assertEqual(len(part1), 4)
        for item in part1:
            self.assertTrue("name" in item)
            name = item["name"]
            self.assertEqual(name[0], '/')
            self.assertTrue(name[-1] != '/')

        # get next batch of 4
        params = {"domain": domain, "Marker": name, "Limit": 4}
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("domains" in rspJson)
        part2 = rspJson["domains"]
        self.assertEqual(len(part2), 4)
        for item in part2:
            self.assertTrue("name" in item)
            name = item["name"]
            self.assertTrue(name != params["Marker"])

        # empty sub-domains
        domain = helper.getTestDomain("tall.h5") + '/'
        params = {"domain": domain}
        rsp = requests.get(req, params=params, headers=headers)
        self.assertEqual(rsp.status_code, 200)
        rspJson = json.loads(rsp.text)
        self.assertTrue("domains" in rspJson)
        domains = rspJson["domains"]
        self.assertEqual(len(domains), 0)

    def testGetTopLevelDomains(self):
        for host in (None, '/'):
            headers = helper.getRequestHeaders(domain=host)
            req = helper.getEndpoint() + '/domains'
            rsp = requests.get(req, headers=headers)
            self.assertEqual(rsp.status_code, 200)
            self.assertEqual(rsp.headers['content-type'], 'application/json')
            domains = rsp.json()["domains"]

            # this should only happen in the very first test run
            # TODO: ^ what?
            if len(domains) == 0:
                warnings.warn(f"no domains found at top level ({host})")

            for item in domains:
                name = item["name"]
                self.assertTrue(name.startsWith('/'))
                self.assertFalse(name.endsWith('/'))
                self.assertTrue("owner" in item)
                self.assertTrue("created" in item)
                self.assertTrue("lastModified" in item)
                self.assertTrue(item["class"] in ("domain", "folder"))

# ----------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()

