from zope import component
from zope.app.component.interfaces import ISite
import zope.event

from Products.CMFCore.utils import getToolByName
from Products.Five.component import disableSite
from five.localsitemanager import make_objectmanager_site

from p4a.subtyper.interfaces import ISubtypeAddedEvent
from p4a.subtyper.interfaces import ISubtypeRemovedEvent

from collective.lineage.interfaces import IChildSite
from collective.lineage.events import ChildSiteCreatedEvent
from collective.lineage.events import ChildSiteRemovedEvent


def reindexObjectProvides(folder):
    pc = getToolByName(folder, 'portal_catalog')
    pc.reindexObject(
        folder,
        idxs=['object_provides']
    )


def enableFolder(folder):
    if not ISite.providedBy(folder):
        make_objectmanager_site(folder)
    # reindex so that the object_provides index is aware of our
    # new interface
    reindexObjectProvides(folder)
    zope.event.notify(ChildSiteCreatedEvent(folder))


def disableFolder(folder):
    # remove local site components
    disableSite(folder)

    # reindex the object so that the object_provides index is
    # aware that we've removed it
    reindexObjectProvides(folder)
    zope.event.notify(ChildSiteRemovedEvent(folder))


@component.adapter(ISubtypeAddedEvent)
def enableChildSite(event):
    """When a lineage folder is created, turn it into a component site
    """
    if not IChildSite.providedBy(event.object):
        return
    folder = event.object
    enableFolder(folder)


@component.adapter(ISubtypeRemovedEvent)
def disableChildSite(event):
    """When a child site is turned off, remove the local components
    """
    if not IChildSite.providedBy(event.object):
        return
    if event.subtype is not None:
        folder = event.object
        disableFolder(folder)

def addURLOverrides(event):
    """When Plone starts up, add our overrides for
        - AbstractCatalogBrain.getURL
        - OFS.Traversable.Traversable.absolute_url
        - OFS.absoluteurl.AbsoluteURL
    """
    # Ideally, we could use `useBrains`,
    # But ZCatalog forces AbstractCatalogBrain first in the MRO.
    from Products.ZCatalog.CatalogBrains import AbstractCatalogBrain
    from collective.lineage import brains
    AbstractCatalogBrain._getURL = AbstractCatalogBrain.getURL
    AbstractCatalogBrain.getURL = brains.getURL

    # The following is required because the stock classes use the
    # context's parent for finding the absolute_url, leading to the
    # navigation root objects themselves not using the stored mapping
    from OFS.absoluteurl import AbsoluteURL, OFSTraversableAbsoluteURL
    from collective.lineage.absoluteurl import LineageAbsoluteURL

    for class_to_patch in (AbsoluteURL, OFSTraversableAbsoluteURL):
        class_to_patch._str = class_to_patch.__str__
        class_to_patch.__str__ = LineageAbsoluteURL.__str__

    from OFS.Traversable import Traversable
    from collective.lineage.absoluteurl import absolute_url

    Traversable._absolute_url = Traversable.absolute_url
    Traversable.absolute_url = absolute_url

    #from zope.app.appsetup.bootstrap import getInformationFromEvent
    #from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
    #from collective.lineage.brains import VHMAwareBrain
    #db, connection, root, root_folder = getInformationFromEvent(event)

    #for obj_id, obj in root_folder.items():
    #    if IPloneSiteRoot.providedBy(obj):
    #        catalog = getToolByName(obj, 'portal_catalog')
    #        catalog._catalog.useBrains(VHMAwareBrain)
