from zope.interface import implements
from zope.interface import alsoProvides

from routes import Mapper
from routes import request_config

from repoze.bfg.interfaces import IRoutesContext
from repoze.bfg.interfaces import IContextNotFound

from zope.deferredimport import deprecated
from zope.deprecation import deprecated as deprecated2

_marker = ()

deprecated(
    "('from repoze.bfg.urldispatch import RoutesContext' is now "
    "deprecated; instead use 'from repoze.bfg.urldispatch import "
    "DefaultRoutesContext')",
    RoutesContext = "repoze.bfg.urldispatch:DefaultRoutesContext",
    )

deprecated2('RoutesMapper',
            'Usage of the ``RoutesMapper`` class is deprecated.  As of '
            'repoze.bfg 0.6.3, you should use the ``<route.. >`` ZCML '
            'directive instead of manually creating a RoutesMapper.')

class DefaultRoutesContext(object):
    implements(IRoutesContext)
    def __init__(self, **kw):
        self.__dict__.update(kw)

class RoutesMapper(object):
    """ The ``RoutesMapper`` is a wrapper for the ``get_root``
    callable passed in to the repoze.bfg ``Router`` at initialization
    time.  When it is instantiated, it wraps the get_root of an
    application in such a way that the `Routes
    <http://routes.groovie.org/index.html>`_ engine has the 'first
    crack' at resolving the current request URL to a repoze.bfg view.
    Any view that claims it is 'for' the interface
    ``repoze.bfg.interfaces.IRoutesContext`` will be called if its
    *name* matches the Routes 'controller' name for the match.  It
    will be passed a context object that has attributes that match the
    Routes match arguments dictionary keys.  If no Routes route
    matches the current request, the 'fallback' get_root is called.

    .. warning:: This class is deprecated.  As of :mod:`repoze.bfg`
       0.6.3, you should use the ``<route.. >`` ZCML directive instead
       of manually creating a RoutesMapper.  See :ref:`urldispatch_chapter`
       for more information.
    """
    def __init__(self, get_root):
        self.get_root = get_root
        self.mapper = Mapper(controller_scan=None, directory=None,
                             explicit=True, always_scan=False)
        self.mapper.explicit = True
        self._regs_created = False

    def __call__(self, environ):
        if not self._regs_created:
            self.mapper.create_regs([])
            self._regs_created = True
        path = environ.get('PATH_INFO', '/')
        self.mapper.environ = environ
        args = self.mapper.match(path)
        if args:
            context_factory = args.get('context_factory', _marker)
            if context_factory is _marker:
                context_factory = DefaultRoutesContext
            else:
                args = args.copy()
                del args['context_factory']
            config = request_config()
            config.mapper = self.mapper
            config.mapper_dict = args
            config.host = environ.get('HTTP_HOST', environ['SERVER_NAME'])
            config.protocol = environ['wsgi.url_scheme']
            config.redirect = None
            context = context_factory(**args)
            alsoProvides(context, IRoutesContext)
            return context

        # fall back to original get_root
        return self.get_root(environ)

    def connect(self, *arg, **kw):
        """ Add a route to the Routes mapper associated with this
        request. This method accepts the same arguments as a Routes
        *Mapper* object.  One differences exists: if the
        ``context_factory`` is passed in with a value as a keyword
        argument, this callable will be called when a model object
        representing the ``context`` for the request needs to be
        constructed.  It will be called with the (all-keyword)
        arguments supplied by the Routes mapper's ``match`` method for
        this route, and should return an instance of a class.  If
        ``context_factory`` is not supplied in this way for a route, a
        default context factory (the ``DefaultRoutesContext`` class)
        will be used.  The interface
        ``repoze.bfg.interfaces.IRoutesContext`` will always be tacked
        on to the context instance in addition to whatever interfaces
        the context instance already supplies.
        """
        
        self.mapper.connect(*arg, **kw)

class RoutesContextNotFound(object):
    implements(IContextNotFound)
    def __init__(self, msg):
        self.msg = msg

class RoutesRootFactory(Mapper):
    """ The ``RoutesRootFactory`` is a wrapper for the ``get_root``
    callable passed in to the repoze.bfg ``Router`` at initialization
    time.  When it is instantiated, it wraps the get_root of an
    application in such a way that the `Routes
    <http://routes.groovie.org/index.html>`_ engine has the 'first
    crack' at resolving the current request URL to a repoze.bfg view.
    Any view that claims it is 'for' the interface
    ``repoze.bfg.interfaces.IRoutesContext`` will be called if its
    *name* matches the Routes ``view_name`` name for the match and any
    of the interfaces named in ``_provides``.  It will be
    passed a context object that has attributes that match the Routes
    match arguments dictionary keys.  If no Routes route matches the
    current request, the 'fallback' get_root is called."""
    def __init__(self, get_root=None, **kw):
        self.get_root = get_root
        kw['controller_scan'] = None
        kw['always_scan'] = False
        kw['directory'] = None
        kw['explicit'] = True
        Mapper.__init__(self, **kw)
        self._regs_created = False

    def has_routes(self):
        return bool(self.matchlist)

    def connect(self, *arg, **kw):
        # we need to deal with our custom attributes specially :-(
        factory = None
        provides = ()
        if '_provides' in kw:
            provides = kw.pop('_provides')
        if '_factory' in kw:
            factory = kw.pop('_factory')
        result = Mapper.connect(self, *arg, **kw)
        self.matchlist[-1]._factory = factory
        self.matchlist[-1]._provides = provides
        return result

    def __call__(self, environ):
        if not self._regs_created:
            self.create_regs([])
            self._regs_created = True
        path = environ.get('PATH_INFO', '/')
        self.environ = environ # sets the thread local
        match = self.routematch(path)
        if match:
            args, route = match
        else:
            args = None
        if args:
            args = args.copy()
            routepath = route.routepath
            factory = route._factory
            if not factory:
                factory = DefaultRoutesContext
            config = request_config()
            config.mapper = self
            config.mapper_dict = args
            config.host = environ.get('HTTP_HOST', environ['SERVER_NAME'])
            config.protocol = environ['wsgi.url_scheme']
            config.redirect = None
            kw = {}
            for k, v in args.items():
                # Routes "helpfully" converts default parameter names
                # into Unicode; these can't be used as attr names
                if k.__class__ is unicode:
                    k = k.encode('utf-8')
                kw[k] = v
            context = factory(**kw)
            environ['wsgiorg.routing_args'] = ((), kw)
            provides = route._provides
            for iface in provides:
                alsoProvides(context, iface)
            alsoProvides(context, IRoutesContext)
            return context

        if self.get_root is None:
            # no fallback get_root
            return RoutesContextNotFound(
                'Routes context cannot be found and no fallback "get_root"')

        # fall back to original get_root
        return self.get_root(environ)
