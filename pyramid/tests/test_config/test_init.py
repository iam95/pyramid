import unittest

from pyramid import testing

import os

here = os.path.dirname(__file__)
locale = os.path.abspath(
    os.path.join(here, '..', 'localeapp', 'locale'))
locale2 = os.path.abspath(
    os.path.join(here, '..', 'localeapp', 'locale2'))
locale3 = os.path.abspath(
    os.path.join(here, '..', 'localeapp', 'locale3'))

from pyramid.tests.test_config import dummy_tween_factory
from pyramid.tests.test_config import dummyfactory
from pyramid.tests.test_config import dummy_include
from pyramid.tests.test_config import dummy_extend
from pyramid.tests.test_config import dummy_extend2
from pyramid.tests.test_config import IDummy
from pyramid.tests.test_config import DummyContext

try:
    import __pypy__
except:
    __pypy__ = None

class ConfiguratorTests(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def _getViewCallable(self, config, ctx_iface=None, request_iface=None,
                         name='', exception_view=False):
        from zope.interface import Interface
        from pyramid.interfaces import IRequest
        from pyramid.interfaces import IView
        from pyramid.interfaces import IViewClassifier
        from pyramid.interfaces import IExceptionViewClassifier
        if exception_view: # pragma: no cover
            classifier = IExceptionViewClassifier
        else:
            classifier = IViewClassifier
        if ctx_iface is None:
            ctx_iface = Interface
        if request_iface is None:
            request_iface = IRequest
        return config.registry.adapters.lookup(
            (classifier, request_iface, ctx_iface), IView, name=name,
            default=None)

    def _registerEventListener(self, config, event_iface=None):
        if event_iface is None: # pragma: no cover
            from zope.interface import Interface
            event_iface = Interface
        L = []
        def subscriber(*event):
            L.extend(event)
        config.registry.registerHandler(subscriber, (event_iface,))
        return L

    def _makeRequest(self, config):
        request = DummyRequest()
        request.registry = config.registry
        return request

    def test_ctor_no_registry(self):
        import sys
        from pyramid.interfaces import ISettings
        from pyramid.config import Configurator
        from pyramid.interfaces import IRendererFactory
        config = Configurator()
        this_pkg = sys.modules['pyramid.tests.test_config']
        self.assertTrue(config.registry.getUtility(ISettings))
        self.assertEqual(config.package, this_pkg)
        config.commit()
        self.assertTrue(config.registry.getUtility(IRendererFactory, 'json'))
        self.assertTrue(config.registry.getUtility(IRendererFactory, 'string'))
        if not __pypy__:
            self.assertTrue(config.registry.getUtility(IRendererFactory, '.pt'))
            self.assertTrue(config.registry.getUtility(IRendererFactory,'.txt'))
        self.assertTrue(config.registry.getUtility(IRendererFactory, '.mak'))
        self.assertTrue(config.registry.getUtility(IRendererFactory, '.mako'))

    def test__set_settings_as_None(self):
        config = self._makeOne()
        settings = config._set_settings(None)
        self.assertTrue(settings)

    def test__set_settings_as_dictwithvalues(self):
        config = self._makeOne()
        settings = config._set_settings({'a':'1'})
        self.assertEqual(settings['a'], '1')

    def test_begin(self):
        from pyramid.config import Configurator
        config = Configurator()
        manager = DummyThreadLocalManager()
        config.manager = manager
        config.begin()
        self.assertEqual(manager.pushed,
                         {'registry':config.registry, 'request':None})
        self.assertEqual(manager.popped, False)

    def test_begin_with_request(self):
        from pyramid.config import Configurator
        config = Configurator()
        request = object()
        manager = DummyThreadLocalManager()
        config.manager = manager
        config.begin(request=request)
        self.assertEqual(manager.pushed,
                         {'registry':config.registry, 'request':request})
        self.assertEqual(manager.popped, False)

    def test_end(self):
        from pyramid.config import Configurator
        config = Configurator()
        manager = DummyThreadLocalManager()
        config.manager = manager
        config.end()
        self.assertEqual(manager.pushed, None)
        self.assertEqual(manager.popped, True)

    def test_ctor_with_package_registry(self):
        import sys
        from pyramid.config import Configurator
        pkg = sys.modules['pyramid']
        config = Configurator(package=pkg)
        self.assertEqual(config.package, pkg)

    def test_ctor_noreg_custom_settings(self):
        from pyramid.interfaces import ISettings
        settings = {'reload_templates':True,
                    'mysetting':True}
        config = self._makeOne(settings=settings)
        settings = config.registry.getUtility(ISettings)
        self.assertEqual(settings['reload_templates'], True)
        self.assertEqual(settings['debug_authorization'], False)
        self.assertEqual(settings['mysetting'], True)

    def test_ctor_noreg_debug_logger_None_default(self):
        from pyramid.interfaces import IDebugLogger
        config = self._makeOne()
        logger = config.registry.getUtility(IDebugLogger)
        self.assertEqual(logger.name, 'pyramid.tests.test_config')

    def test_ctor_noreg_debug_logger_non_None(self):
        from pyramid.interfaces import IDebugLogger
        logger = object()
        config = self._makeOne(debug_logger=logger)
        result = config.registry.getUtility(IDebugLogger)
        self.assertEqual(logger, result)

    def test_ctor_authentication_policy(self):
        from pyramid.interfaces import IAuthenticationPolicy
        policy = object()
        config = self._makeOne(authentication_policy=policy)
        config.commit()
        result = config.registry.getUtility(IAuthenticationPolicy)
        self.assertEqual(policy, result)

    def test_ctor_authorization_policy_only(self):
        from zope.configuration.config import ConfigurationExecutionError
        policy = object()
        config = self._makeOne(authorization_policy=policy)
        self.assertRaises(ConfigurationExecutionError, config.commit)

    def test_ctor_no_root_factory(self):
        from pyramid.interfaces import IRootFactory
        config = self._makeOne()
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)

    def test_ctor_with_root_factory(self):
        from pyramid.interfaces import IRootFactory
        factory = object()
        config = self._makeOne(root_factory=factory)
        self.assertEqual(config.registry.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(config.registry.queryUtility(IRootFactory), factory)

    def test_ctor_alternate_renderers(self):
        from pyramid.interfaces import IRendererFactory
        renderer = object()
        config = self._makeOne(renderers=[('yeah', renderer)])
        config.commit()
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'yeah'),
                         renderer)

    def test_ctor_default_renderers(self):
        from pyramid.interfaces import IRendererFactory
        from pyramid.renderers import json_renderer_factory
        config = self._makeOne()
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'json'),
                         json_renderer_factory)

    def test_ctor_default_permission(self):
        from pyramid.interfaces import IDefaultPermission
        config = self._makeOne(default_permission='view')
        config.commit()
        self.assertEqual(config.registry.getUtility(IDefaultPermission), 'view')

    def test_ctor_session_factory(self):
        from pyramid.interfaces import ISessionFactory
        factory = object()
        config = self._makeOne(session_factory=factory)
        self.assertEqual(config.registry.queryUtility(ISessionFactory), None)
        config.commit()
        self.assertEqual(config.registry.getUtility(ISessionFactory), factory)

    def test_ctor_default_view_mapper(self):
        from pyramid.interfaces import IViewMapperFactory
        mapper = object()
        config = self._makeOne(default_view_mapper=mapper)
        config.commit()
        self.assertEqual(config.registry.getUtility(IViewMapperFactory),
                         mapper)

    def test_ctor_httpexception_view_default(self):
        from pyramid.interfaces import IExceptionResponse
        from pyramid.httpexceptions import default_exceptionresponse_view
        from pyramid.interfaces import IRequest
        config = self._makeOne()
        view = self._getViewCallable(config,
                                     ctx_iface=IExceptionResponse,
                                     request_iface=IRequest)
        self.assertTrue(view.__wraps__ is default_exceptionresponse_view)

    def test_ctor_exceptionresponse_view_None(self):
        from pyramid.interfaces import IExceptionResponse
        from pyramid.interfaces import IRequest
        config = self._makeOne(exceptionresponse_view=None)
        view = self._getViewCallable(config,
                                     ctx_iface=IExceptionResponse,
                                     request_iface=IRequest)
        self.assertTrue(view is None)

    def test_ctor_exceptionresponse_view_custom(self):
        from pyramid.interfaces import IExceptionResponse
        from pyramid.interfaces import IRequest
        def exceptionresponse_view(context, request): pass
        config = self._makeOne(exceptionresponse_view=exceptionresponse_view)
        view = self._getViewCallable(config,
                                     ctx_iface=IExceptionResponse,
                                     request_iface=IRequest)
        self.assertTrue(view.__wraps__ is exceptionresponse_view)

    def test_with_package_module(self):
        from pyramid.tests.test_config import test_init
        import pyramid.tests
        config = self._makeOne()
        newconfig = config.with_package(test_init)
        self.assertEqual(newconfig.package, pyramid.tests.test_config)

    def test_with_package_package(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        newconfig = config.with_package(pyramid.tests.test_config)
        self.assertEqual(newconfig.package, pyramid.tests.test_config)

    def test_with_package_context_is_not_None(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        config._ctx = DummyContext()
        config._ctx.registry = None
        config._ctx.autocommit = True
        config._ctx.route_prefix = None
        newconfig = config.with_package(pyramid.tests.test_config)
        self.assertEqual(newconfig.package, pyramid.tests.test_config)

    def test_with_package_context_is_None(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        config._ctx = None
        newconfig = config.with_package(pyramid.tests.test_config)
        self.assertEqual(newconfig.package, pyramid.tests.test_config)
        self.assertEqual(config._ctx.package, None)

    def test_maybe_dotted_string_success(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        result = config.maybe_dotted('pyramid.tests.test_config')
        self.assertEqual(result, pyramid.tests.test_config)

    def test_maybe_dotted_string_fail(self):
        config = self._makeOne()
        self.assertRaises(ImportError,
                          config.maybe_dotted, 'cant.be.found')

    def test_maybe_dotted_notstring_success(self):
        import pyramid.tests.test_config
        config = self._makeOne()
        result = config.maybe_dotted(pyramid.tests.test_config)
        self.assertEqual(result, pyramid.tests.test_config)

    def test_absolute_asset_spec_already_absolute(self):
        import pyramid.tests.test_config
        config = self._makeOne(package=pyramid.tests.test_config)
        result = config.absolute_asset_spec('already:absolute')
        self.assertEqual(result, 'already:absolute')

    def test_absolute_asset_spec_notastring(self):
        import pyramid.tests.test_config
        config = self._makeOne(package=pyramid.tests.test_config)
        result = config.absolute_asset_spec(None)
        self.assertEqual(result, None)

    def test_absolute_asset_spec_relative(self):
        import pyramid.tests.test_config
        config = self._makeOne(package=pyramid.tests.test_config)
        result = config.absolute_asset_spec('files')
        self.assertEqual(result, 'pyramid.tests.test_config:files')

    def test__fix_registry_has_listeners(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertEqual(reg.has_listeners, True)

    def test__fix_registry_notify(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertEqual(reg.notify(1), None)
        self.assertEqual(reg.events, (1,))

    def test__fix_registry_queryAdapterOrSelf(self):
        from zope.interface import Interface
        class IFoo(Interface):
            pass
        class Foo(object):
            implements(IFoo)
        class Bar(object):
            pass
        adaptation = ()
        foo = Foo()
        bar = Bar()
        reg = DummyRegistry(adaptation)
        config = self._makeOne(reg)
        config._fix_registry()
        self.assertTrue(reg.queryAdapterOrSelf(foo, IFoo) is foo)
        self.assertTrue(reg.queryAdapterOrSelf(bar, IFoo) is adaptation)

    def test__fix_registry_registerSelfAdapter(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config._fix_registry()
        reg.registerSelfAdapter('required', 'provided', name='abc')
        self.assertEqual(len(reg.adapters), 1)
        args, kw = reg.adapters[0]
        self.assertEqual(args[0]('abc'), 'abc')
        self.assertEqual(kw,
                         {'info': u'', 'provided': 'provided',
                          'required': 'required', 'name': 'abc', 'event': True})

    def test_setup_registry_calls_fix_registry(self):
        reg = DummyRegistry()
        config = self._makeOne(reg)
        config.add_view = lambda *arg, **kw: False
        config._add_tween = lambda *arg, **kw: False
        config.setup_registry()
        self.assertEqual(reg.has_listeners, True)

    def test_setup_registry_registers_default_exceptionresponse_view(self):
        from webob.exc import WSGIHTTPException
        from pyramid.interfaces import IExceptionResponse
        from pyramid.view import default_exceptionresponse_view
        reg = DummyRegistry()
        config = self._makeOne(reg)
        views = []
        config.add_view = lambda *arg, **kw: views.append((arg, kw))
        config._add_tween = lambda *arg, **kw: False
        config.setup_registry()
        self.assertEqual(views[0], ((default_exceptionresponse_view,),
                                    {'context':IExceptionResponse}))
        self.assertEqual(views[1], ((default_exceptionresponse_view,),
                                    {'context':WSGIHTTPException}))

    def test_setup_registry_registers_default_webob_iresponse_adapter(self):
        from webob import Response
        from pyramid.interfaces import IResponse
        config = self._makeOne()
        config.setup_registry()
        response = Response()
        self.assertTrue(
            config.registry.queryAdapter(response, IResponse) is response)

    def test_setup_registry_explicit_notfound_trumps_iexceptionresponse(self):
        from pyramid.renderers import null_renderer
        from zope.interface import implementedBy
        from pyramid.interfaces import IRequest
        from pyramid.httpexceptions import HTTPNotFound
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg, autocommit=True)
        config.setup_registry() # registers IExceptionResponse default view
        def myview(context, request):
            return 'OK'
        config.add_view(myview, context=HTTPNotFound, renderer=null_renderer)
        request = self._makeRequest(config)
        view = self._getViewCallable(config,
                                     ctx_iface=implementedBy(HTTPNotFound),
                                     request_iface=IRequest)
        result = view(None, request)
        self.assertEqual(result, 'OK')

    def test_setup_registry_custom_settings(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ISettings
        settings = {'reload_templates':True,
                    'mysetting':True}
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(settings=settings)
        settings = reg.getUtility(ISettings)
        self.assertEqual(settings['reload_templates'], True)
        self.assertEqual(settings['debug_authorization'], False)
        self.assertEqual(settings['mysetting'], True)

    def test_setup_registry_debug_logger_None_default(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDebugLogger
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry()
        logger = reg.getUtility(IDebugLogger)
        self.assertEqual(logger.name, 'pyramid.tests.test_config')

    def test_setup_registry_debug_logger_non_None(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDebugLogger
        logger = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(debug_logger=logger)
        result = reg.getUtility(IDebugLogger)
        self.assertEqual(logger, result)

    def test_setup_registry_debug_logger_name(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDebugLogger
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(debug_logger='foo')
        result = reg.getUtility(IDebugLogger)
        self.assertEqual(result.name, 'foo')

    def test_setup_registry_authentication_policy(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IAuthenticationPolicy
        policy = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(authentication_policy=policy)
        config.commit()
        result = reg.getUtility(IAuthenticationPolicy)
        self.assertEqual(policy, result)

    def test_setup_registry_authentication_policy_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IAuthenticationPolicy
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(authentication_policy='pyramid.tests.test_config')
        config.commit()
        result = reg.getUtility(IAuthenticationPolicy)
        import pyramid.tests.test_config
        self.assertEqual(result, pyramid.tests.test_config)

    def test_setup_registry_authorization_policy_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IAuthorizationPolicy
        reg = Registry()
        config = self._makeOne(reg)
        dummy = object()
        config.setup_registry(authentication_policy=dummy,
                              authorization_policy='pyramid.tests.test_config')
        config.commit()
        result = reg.getUtility(IAuthorizationPolicy)
        import pyramid.tests.test_config
        self.assertEqual(result, pyramid.tests.test_config)

    def test_setup_registry_authorization_policy_only(self):
        from zope.configuration.config import ConfigurationExecutionError
        from pyramid.registry import Registry
        policy = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(authorization_policy=policy)
        config = self.assertRaises(ConfigurationExecutionError, config.commit)

    def test_setup_registry_no_default_root_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRootFactory
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry()
        config.commit()
        self.assertEqual(reg.queryUtility(IRootFactory), None)

    def test_setup_registry_dottedname_root_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRootFactory
        reg = Registry()
        config = self._makeOne(reg)
        import pyramid.tests.test_config
        config.setup_registry(root_factory='pyramid.tests.test_config')
        self.assertEqual(reg.queryUtility(IRootFactory), None)
        config.commit()
        self.assertEqual(reg.getUtility(IRootFactory),
                         pyramid.tests.test_config)

    def test_setup_registry_locale_negotiator_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ILocaleNegotiator
        reg = Registry()
        config = self._makeOne(reg)
        import pyramid.tests.test_config
        config.setup_registry(locale_negotiator='pyramid.tests.test_config')
        self.assertEqual(reg.queryUtility(ILocaleNegotiator), None)
        config.commit()
        utility = reg.getUtility(ILocaleNegotiator)
        self.assertEqual(utility, pyramid.tests.test_config)

    def test_setup_registry_locale_negotiator(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import ILocaleNegotiator
        reg = Registry()
        config = self._makeOne(reg)
        negotiator = object()
        config.setup_registry(locale_negotiator=negotiator)
        self.assertEqual(reg.queryUtility(ILocaleNegotiator), None)
        config.commit()
        utility = reg.getUtility(ILocaleNegotiator)
        self.assertEqual(utility, negotiator)

    def test_setup_registry_request_factory(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRequestFactory
        reg = Registry()
        config = self._makeOne(reg)
        factory = object()
        config.setup_registry(request_factory=factory)
        self.assertEqual(reg.queryUtility(IRequestFactory), None)
        config.commit()
        utility = reg.getUtility(IRequestFactory)
        self.assertEqual(utility, factory)

    def test_setup_registry_request_factory_dottedname(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRequestFactory
        reg = Registry()
        config = self._makeOne(reg)
        import pyramid.tests.test_config
        config.setup_registry(request_factory='pyramid.tests.test_config')
        self.assertEqual(reg.queryUtility(IRequestFactory), None)
        config.commit()
        utility = reg.getUtility(IRequestFactory)
        self.assertEqual(utility, pyramid.tests.test_config)

    def test_setup_registry_renderer_globals_factory(self):
        import warnings
        warnings.filterwarnings('ignore')
        try:
            from pyramid.registry import Registry
            from pyramid.interfaces import IRendererGlobalsFactory
            reg = Registry()
            config = self._makeOne(reg)
            factory = object()
            config.setup_registry(renderer_globals_factory=factory)
            self.assertEqual(reg.queryUtility(IRendererGlobalsFactory), None)
            config.commit()
            utility = reg.getUtility(IRendererGlobalsFactory)
            self.assertEqual(utility, factory)
        finally:
            warnings.resetwarnings()

    def test_setup_registry_renderer_globals_factory_dottedname(self):
        import warnings
        warnings.filterwarnings('ignore')
        try:
            from pyramid.registry import Registry
            from pyramid.interfaces import IRendererGlobalsFactory
            reg = Registry()
            config = self._makeOne(reg)
            import pyramid.tests.test_config
            config.setup_registry(
                renderer_globals_factory='pyramid.tests.test_config')
            self.assertEqual(reg.queryUtility(IRendererGlobalsFactory), None)
            config.commit()
            utility = reg.getUtility(IRendererGlobalsFactory)
            self.assertEqual(utility, pyramid.tests.test_config)
        finally:
            warnings.resetwarnings()

    def test_setup_registry_alternate_renderers(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IRendererFactory
        renderer = object()
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(renderers=[('yeah', renderer)])
        config.commit()
        self.assertEqual(reg.getUtility(IRendererFactory, 'yeah'),
                         renderer)

    def test_setup_registry_default_permission(self):
        from pyramid.registry import Registry
        from pyramid.interfaces import IDefaultPermission
        reg = Registry()
        config = self._makeOne(reg)
        config.setup_registry(default_permission='view')
        config.commit()
        self.assertEqual(reg.getUtility(IDefaultPermission), 'view')

    def test_setup_registry_includes(self):
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        settings = {
            'pyramid.includes':
"""pyramid.tests.test_config.dummy_include
pyramid.tests.test_config.dummy_include2""",
        }
        config.setup_registry(settings=settings)
        self.assert_(reg.included)
        self.assert_(reg.also_included)

    def test_setup_registry_includes_spaces(self):
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        settings = {
            'pyramid.includes':
"""pyramid.tests.test_config.dummy_include pyramid.tests.test_config.dummy_include2""",
        }
        config.setup_registry(settings=settings)
        self.assert_(reg.included)
        self.assert_(reg.also_included)

    def test_setup_registry_tweens(self):
        from pyramid.interfaces import ITweens
        from pyramid.registry import Registry
        reg = Registry()
        config = self._makeOne(reg)
        settings = {
            'pyramid.tweens':
                    'pyramid.tests.test_config.dummy_tween_factory'
        }
        config.setup_registry(settings=settings)
        config.commit()
        tweens = config.registry.getUtility(ITweens)
        self.assertEqual(
            tweens.explicit,
            [('pyramid.tests.test_config.dummy_tween_factory',
              dummy_tween_factory)])

    def test_make_wsgi_app(self):
        import pyramid.config
        from pyramid.router import Router
        from pyramid.interfaces import IApplicationCreated
        manager = DummyThreadLocalManager()
        config = self._makeOne()
        subscriber = self._registerEventListener(config, IApplicationCreated)
        config.manager = manager
        app = config.make_wsgi_app()
        self.assertEqual(app.__class__, Router)
        self.assertEqual(manager.pushed['registry'], config.registry)
        self.assertEqual(manager.pushed['request'], None)
        self.assertTrue(manager.popped)
        self.assertEqual(pyramid.config.global_registries.last, app.registry)
        self.assertEqual(len(subscriber), 1)
        self.assertTrue(IApplicationCreated.providedBy(subscriber[0]))
        pyramid.config.global_registries.empty()

    def test_include_with_dotted_name(self):
        from pyramid.tests import test_config
        config = self._makeOne()
        context_before = config._make_context()
        config._ctx = context_before
        config.include('pyramid.tests.test_config.dummy_include')
        context_after = config._ctx
        actions = context_after.actions
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            context_after.actions[0][:3],
            ('discrim', None, test_config),
            )
        self.assertEqual(context_after.basepath, None)
        self.assertEqual(context_after.includepath, ())
        self.assertTrue(context_after is context_before)

    def test_include_with_python_callable(self):
        from pyramid.tests import test_config
        config = self._makeOne()
        context_before = config._make_context()
        config._ctx = context_before
        config.include(dummy_include)
        context_after = config._ctx
        actions = context_after.actions
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0][:3],
            ('discrim', None, test_config),
            )
        self.assertEqual(context_after.basepath, None)
        self.assertEqual(context_after.includepath, ())
        self.assertTrue(context_after is context_before)

    def test_include_with_module_defaults_to_includeme(self):
        from pyramid.tests import test_config
        config = self._makeOne()
        context_before = config._make_context()
        config._ctx = context_before
        config.include('pyramid.tests.test_config')
        context_after = config._ctx
        actions = context_after.actions
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            actions[0][:3],
            ('discrim', None, test_config),
            )
        self.assertEqual(context_after.basepath, None)
        self.assertEqual(context_after.includepath, ())
        self.assertTrue(context_after is context_before)

    def test_include_with_route_prefix(self):
        root_config = self._makeOne(autocommit=True)
        def dummy_subapp(config):
            self.assertEqual(config.route_prefix, 'root')
        root_config.include(dummy_subapp, route_prefix='root')

    def test_include_with_nested_route_prefix(self):
        root_config = self._makeOne(autocommit=True, route_prefix='root')
        def dummy_subapp(config):
            self.assertEqual(config.route_prefix, 'root/nested')
        root_config.include(dummy_subapp, route_prefix='nested')

    def test_with_context(self):
        config = self._makeOne()
        ctx = config._make_context()
        newconfig = config.with_context(ctx)
        self.assertEqual(newconfig._ctx, ctx)

    def test_action_branching_kw_is_None(self):
        config = self._makeOne(autocommit=True)
        self.assertEqual(config.action('discrim'), None)

    def test_action_branching_kw_is_not_None(self):
        config = self._makeOne(autocommit=True)
        self.assertEqual(config.action('discrim', kw={'a':1}), None)

    def test_action_branching_nonautocommit_without_context_info(self):
        config = self._makeOne(autocommit=False)
        config._ctx = DummyContext()
        config._ctx.info = None
        config._ctx.autocommit = False
        config._ctx.actions = []
        self.assertEqual(config.action('discrim', kw={'a':1}), None)
        self.assertEqual(config._ctx.actions, [('discrim', None, (), {'a': 1})])
        # info is not set on ctx, it's set on the groupingcontextdecorator,
        # and then lost

    def test_action_branching_nonautocommit_with_context_info(self):
        config = self._makeOne(autocommit=False)
        config._ctx = DummyContext()
        config._ctx.info = 'abc'
        config._ctx.autocommit = False
        config._ctx.actions = []
        config._ctx.action = lambda *arg, **kw: self.assertEqual(
            arg,
            ('discrim', None, (), {'a': 1}, 0))
        self.assertEqual(config.action('discrim', kw={'a':1}), None)
        self.assertEqual(config._ctx.actions, [])
        self.assertEqual(config._ctx.info, 'abc')

    def test_set_renderer_globals_factory(self):
        import warnings
        warnings.filterwarnings('ignore')
        try:
            from pyramid.interfaces import IRendererGlobalsFactory
            config = self._makeOne(autocommit=True)
            factory = object()
            config.set_renderer_globals_factory(factory)
            self.assertEqual(
                config.registry.getUtility(IRendererGlobalsFactory),
                factory)
        finally:
            warnings.resetwarnings()

    def test_set_renderer_globals_factory_dottedname(self):
        import warnings
        warnings.filterwarnings('ignore')
        try:
            from pyramid.interfaces import IRendererGlobalsFactory
            config = self._makeOne(autocommit=True)
            config.set_renderer_globals_factory(
                'pyramid.tests.test_config.dummyfactory')
            self.assertEqual(
                config.registry.getUtility(IRendererGlobalsFactory),
                dummyfactory)
        finally:
            warnings.resetwarnings()

    def test_set_default_permission(self):
        from pyramid.interfaces import IDefaultPermission
        config = self._makeOne(autocommit=True)
        config.set_default_permission('view')
        self.assertEqual(config.registry.getUtility(IDefaultPermission),
                         'view')

    def test_set_locale_negotiator(self):
        from pyramid.interfaces import ILocaleNegotiator
        config = self._makeOne(autocommit=True)
        def negotiator(request): pass
        config.set_locale_negotiator(negotiator)
        self.assertEqual(config.registry.getUtility(ILocaleNegotiator),
                         negotiator)

    def test_set_locale_negotiator_dottedname(self):
        from pyramid.interfaces import ILocaleNegotiator
        config = self._makeOne(autocommit=True)
        config.set_locale_negotiator(
            'pyramid.tests.test_config.dummyfactory')
        self.assertEqual(config.registry.getUtility(ILocaleNegotiator),
                         dummyfactory)

    def test_add_translation_dirs_missing_dir(self):
        from pyramid.exceptions import ConfigurationError
        config = self._makeOne()
        self.assertRaises(ConfigurationError,
                          config.add_translation_dirs,
                          '/wont/exist/on/my/system')

    def test_add_translation_dirs_no_specs(self):
        from pyramid.interfaces import ITranslationDirectories
        from pyramid.interfaces import IChameleonTranslate
        config = self._makeOne()
        config.add_translation_dirs()
        self.assertEqual(config.registry.queryUtility(ITranslationDirectories),
                         None)
        self.assertEqual(config.registry.queryUtility(IChameleonTranslate),
                         None)

    def test_add_translation_dirs_asset_spec(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs('pyramid.tests.localeapp:locale')
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale])

    def test_add_translation_dirs_asset_spec_existing_translation_dirs(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        directories = ['abc']
        config.registry.registerUtility(directories, ITranslationDirectories)
        config.add_translation_dirs('pyramid.tests.localeapp:locale')
        result = config.registry.getUtility(ITranslationDirectories)
        self.assertEqual(result, [locale, 'abc'])

    def test_add_translation_dirs_multiple_specs(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs('pyramid.tests.localeapp:locale',
                                    'pyramid.tests.localeapp:locale2')
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale, locale2])

    def test_add_translation_dirs_multiple_specs_multiple_calls(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs('pyramid.tests.localeapp:locale',
                                    'pyramid.tests.localeapp:locale2')
        config.add_translation_dirs('pyramid.tests.localeapp:locale3')
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale3, locale, locale2])

    def test_add_translation_dirs_registers_chameleon_translate(self):
        from pyramid.interfaces import IChameleonTranslate
        from pyramid.threadlocal import manager
        request = DummyRequest()
        config = self._makeOne(autocommit=True)
        manager.push({'request':request, 'registry':config.registry})
        try:
            config.add_translation_dirs('pyramid.tests.localeapp:locale')
            translate = config.registry.getUtility(IChameleonTranslate)
            self.assertEqual(translate('Approve'), u'Approve')
        finally:
            manager.pop()

    def test_add_translation_dirs_abspath(self):
        from pyramid.interfaces import ITranslationDirectories
        config = self._makeOne(autocommit=True)
        config.add_translation_dirs(locale)
        self.assertEqual(config.registry.getUtility(ITranslationDirectories),
                         [locale])

    def test_add_renderer(self):
        from pyramid.interfaces import IRendererFactory
        config = self._makeOne(autocommit=True)
        renderer = object()
        config.add_renderer('name', renderer)
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'name'),
                         renderer)

    def test_add_renderer_dottedname_factory(self):
        from pyramid.interfaces import IRendererFactory
        config = self._makeOne(autocommit=True)
        import pyramid.tests.test_config
        config.add_renderer('name', 'pyramid.tests.test_config')
        self.assertEqual(config.registry.getUtility(IRendererFactory, 'name'),
                         pyramid.tests.test_config)

    def test_scan_integration(self):
        import os
        from zope.interface import alsoProvides
        from pyramid.interfaces import IRequest
        from pyramid.view import render_view_to_response
        import pyramid.tests.test_config.pkgs.scannable as package
        config = self._makeOne(autocommit=True)
        config.scan(package)

        ctx = DummyContext()
        req = DummyRequest()
        alsoProvides(req, IRequest)
        req.registry = config.registry

        req.method = 'GET'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked')

        req.method = 'POST'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked_post')

        result= render_view_to_response(ctx, req, 'grokked_class')
        self.assertEqual(result, 'grokked_class')

        result= render_view_to_response(ctx, req, 'grokked_instance')
        self.assertEqual(result, 'grokked_instance')

        result= render_view_to_response(ctx, req, 'oldstyle_grokked_class')
        self.assertEqual(result, 'oldstyle_grokked_class')

        req.method = 'GET'
        result = render_view_to_response(ctx, req, 'another')
        self.assertEqual(result, 'another_grokked')

        req.method = 'POST'
        result = render_view_to_response(ctx, req, 'another')
        self.assertEqual(result, 'another_grokked_post')

        result= render_view_to_response(ctx, req, 'another_grokked_class')
        self.assertEqual(result, 'another_grokked_class')

        result= render_view_to_response(ctx, req, 'another_grokked_instance')
        self.assertEqual(result, 'another_grokked_instance')

        result= render_view_to_response(ctx, req,
                                        'another_oldstyle_grokked_class')
        self.assertEqual(result, 'another_oldstyle_grokked_class')

        result = render_view_to_response(ctx, req, 'stacked1')
        self.assertEqual(result, 'stacked')

        result = render_view_to_response(ctx, req, 'stacked2')
        self.assertEqual(result, 'stacked')

        result = render_view_to_response(ctx, req, 'another_stacked1')
        self.assertEqual(result, 'another_stacked')

        result = render_view_to_response(ctx, req, 'another_stacked2')
        self.assertEqual(result, 'another_stacked')

        result = render_view_to_response(ctx, req, 'stacked_class1')
        self.assertEqual(result, 'stacked_class')

        result = render_view_to_response(ctx, req, 'stacked_class2')
        self.assertEqual(result, 'stacked_class')

        result = render_view_to_response(ctx, req, 'another_stacked_class1')
        self.assertEqual(result, 'another_stacked_class')

        result = render_view_to_response(ctx, req, 'another_stacked_class2')
        self.assertEqual(result, 'another_stacked_class')

        if not os.name.startswith('java'):
            # on Jython, a class without an __init__ apparently accepts
            # any number of arguments without raising a TypeError.

            self.assertRaises(TypeError,
                              render_view_to_response, ctx, req, 'basemethod')

        result = render_view_to_response(ctx, req, 'method1')
        self.assertEqual(result, 'method1')

        result = render_view_to_response(ctx, req, 'method2')
        self.assertEqual(result, 'method2')

        result = render_view_to_response(ctx, req, 'stacked_method1')
        self.assertEqual(result, 'stacked_method')

        result = render_view_to_response(ctx, req, 'stacked_method2')
        self.assertEqual(result, 'stacked_method')

        result = render_view_to_response(ctx, req, 'subpackage_init')
        self.assertEqual(result, 'subpackage_init')

        result = render_view_to_response(ctx, req, 'subpackage_notinit')
        self.assertEqual(result, 'subpackage_notinit')

        result = render_view_to_response(ctx, req, 'subsubpackage_init')
        self.assertEqual(result, 'subsubpackage_init')

        result = render_view_to_response(ctx, req, 'pod_notinit')
        self.assertEqual(result, None)

    def test_scan_integration_dottedname_package(self):
        from zope.interface import alsoProvides
        from pyramid.interfaces import IRequest
        from pyramid.view import render_view_to_response
        config = self._makeOne(autocommit=True)
        config.scan('pyramid.tests.test_config.pkgs.scannable')

        ctx = DummyContext()
        req = DummyRequest()
        alsoProvides(req, IRequest)
        req.registry = config.registry

        req.method = 'GET'
        result = render_view_to_response(ctx, req, '')
        self.assertEqual(result, 'grokked')

    def test_scan_integration_with_extra_kw(self):
        config = self._makeOne(autocommit=True)
        config.scan('pyramid.tests.test_config.pkgs.scanextrakw', a=1)
        self.assertEqual(config.a, 1)

    def test_scan_integration_with_onerror(self):
        # fancy sys.path manipulation here to appease "setup.py test" which
        # fails miserably when it can't import something in the package
        import sys
        try:
            here = os.path.dirname(__file__)
            path = os.path.join(here, 'path')
            sys.path.append(path)
            config = self._makeOne(autocommit=True)
            class FooException(Exception):
                pass
            def onerror(name):
                raise FooException
            self.assertRaises(FooException, config.scan, 'scanerror',
                              onerror=onerror)
        finally:
            sys.path.remove(path)

    def test_scan_integration_conflict(self):
        from zope.configuration.config import ConfigurationConflictError
        from pyramid.tests.test_config.pkgs import selfscan
        from pyramid.config import Configurator
        c = Configurator()
        c.scan(selfscan)
        c.scan(selfscan)
        try:
            c.commit()
        except ConfigurationConflictError, why:
            def scanconflicts(e):
                conflicts = e._conflicts.values()
                for conflict in conflicts:
                    for confinst in conflict:
                        yield confinst[3]
            which = list(scanconflicts(why))
            self.assertEqual(len(which), 4)
            self.assertTrue("@view_config(renderer='string')" in which)
            self.assertTrue("@view_config(name='two', renderer='string')" in
                            which)

    def test_hook_zca(self):
        from zope.component import getSiteManager
        def foo():
            '123'
        try:
            config = self._makeOne()
            config.hook_zca()
            config.begin()
            sm = getSiteManager()
            self.assertEqual(sm, config.registry)
        finally:
            getSiteManager.reset()

    def test_unhook_zca(self):
        from zope.component import getSiteManager
        def foo():
            '123'
        try:
            getSiteManager.sethook(foo)
            config = self._makeOne()
            config.unhook_zca()
            sm = getSiteManager()
            self.assertNotEqual(sm, '123')
        finally:
            getSiteManager.reset()
        

    def test_commit_conflict_simple(self):
        from zope.configuration.config import ConfigurationConflictError
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.add_view(view1)
        config.add_view(view2)
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_commit_conflict_resolved_with_include(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        def includeme(config):
            config.add_view(view2)
        config.add_view(view1)
        config.include(includeme)
        config.commit()
        registeredview = self._getViewCallable(config)
        self.assertEqual(registeredview.__name__, 'view1')

    def test_commit_conflict_with_two_includes(self):
        from zope.configuration.config import ConfigurationConflictError
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        def includeme1(config):
            config.add_view(view1)
        def includeme2(config):
            config.add_view(view2)
        config.include(includeme1)
        config.include(includeme2)
        try:
            config.commit()
        except ConfigurationConflictError, why:
            c1, c2 = _conflictFunctions(why)
            self.assertEqual(c1, 'includeme1')
            self.assertEqual(c2, 'includeme2')
        else: #pragma: no cover
            raise AssertionError

    def test_commit_conflict_resolved_with_two_includes_and_local(self):
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        def view3(request): pass
        def includeme1(config):
            config.add_view(view1)
        def includeme2(config):
            config.add_view(view2)
        config.include(includeme1)
        config.include(includeme2)
        config.add_view(view3)
        config.commit()
        registeredview = self._getViewCallable(config)
        self.assertEqual(registeredview.__name__, 'view3')

    def test_autocommit_no_conflicts(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        def view1(request): pass
        def view2(request): pass
        def view3(request): pass
        config.add_view(view1, renderer=null_renderer)
        config.add_view(view2, renderer=null_renderer)
        config.add_view(view3, renderer=null_renderer)
        config.commit()
        registeredview = self._getViewCallable(config)
        self.assertEqual(registeredview.__name__, 'view3')

    def test_conflict_set_notfound_view(self):
        from zope.configuration.config import ConfigurationConflictError
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.set_notfound_view(view1)
        config.set_notfound_view(view2)
        try:
            config.commit()
        except ConfigurationConflictError, why:
            c1, c2 = _conflictFunctions(why)
            self.assertEqual(c1, 'test_conflict_set_notfound_view')
            self.assertEqual(c2, 'test_conflict_set_notfound_view')
        else: # pragma: no cover
            raise AssertionError

    def test_conflict_set_forbidden_view(self):
        from zope.configuration.config import ConfigurationConflictError
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.set_forbidden_view(view1)
        config.set_forbidden_view(view2)
        try:
            config.commit()
        except ConfigurationConflictError, why:
            c1, c2 = _conflictFunctions(why)
            self.assertEqual(c1, 'test_conflict_set_forbidden_view')
            self.assertEqual(c2, 'test_conflict_set_forbidden_view')
        else: # pragma: no cover
            raise AssertionError

    def test___getattr__missing_when_directives_exist(self):
        config = self._makeOne()
        directives = {}
        config.registry._directives = directives
        self.assertRaises(AttributeError, config.__getattr__, 'wontexist')

    def test___getattr__missing_when_directives_dont_exist(self):
        config = self._makeOne()
        self.assertRaises(AttributeError, config.__getattr__, 'wontexist')

    def test___getattr__matches(self):
        config = self._makeOne()
        def foo(config): pass
        directives = {'foo':(foo, True)}
        config.registry._directives = directives
        foo_meth = config.foo
        self.assertTrue(foo_meth.im_func.__docobj__ is foo)

    def test___getattr__matches_no_action_wrap(self):
        config = self._makeOne()
        def foo(config): pass
        directives = {'foo':(foo, False)}
        config.registry._directives = directives
        foo_meth = config.foo
        self.assertTrue(foo_meth.im_func is foo)

class TestConfiguratorDeprecatedFeatures(unittest.TestCase):
    def setUp(self):
        import warnings
        warnings.filterwarnings('ignore')

    def tearDown(self):
        import warnings
        warnings.resetwarnings()

    def _makeOne(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        config.registry._dont_resolve_responses = True
        return config
    
    def _getRouteRequestIface(self, config, name):
        from pyramid.interfaces import IRouteRequest
        iface = config.registry.getUtility(IRouteRequest, name)
        return iface

    def _getViewCallable(self, config, ctx_iface=None, request_iface=None,
                         name='', exception_view=False):
        from zope.interface import Interface
        from pyramid.interfaces import IView
        from pyramid.interfaces import IViewClassifier
        from pyramid.interfaces import IExceptionViewClassifier
        if exception_view:
            classifier = IExceptionViewClassifier
        else:
            classifier = IViewClassifier
        if ctx_iface is None:
            ctx_iface = Interface
        return config.registry.adapters.lookup(
            (classifier, request_iface, ctx_iface), IView, name=name,
            default=None)

    def _registerRenderer(self, config, name='.txt'):
        from pyramid.interfaces import IRendererFactory
        from pyramid.interfaces import ITemplateRenderer
        from zope.interface import implements
        class Renderer:
            implements(ITemplateRenderer)
            def __init__(self, info):
                self.__class__.info = info
            def __call__(self, *arg):
                return 'Hello!'
        config.registry.registerUtility(Renderer, IRendererFactory, name=name)
        return Renderer

    def _assertRoute(self, config, name, path, num_predicates=0):
        from pyramid.interfaces import IRoutesMapper
        mapper = config.registry.getUtility(IRoutesMapper)
        routes = mapper.get_routes()
        route = routes[0]
        self.assertEqual(len(routes), 1)
        self.assertEqual(route.name, name)
        self.assertEqual(route.path, path)
        self.assertEqual(len(routes[0].predicates), num_predicates)
        return route

    def _makeRequest(self, config):
        request = DummyRequest()
        request.registry = config.registry
        return request

    def test_add_route_with_view(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, view_renderer=null_renderer)
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, None, request_type)
        self.assertEqual(wrapper(None, None), 'OK')
        self._assertRoute(config, 'name', 'path')

    def test_add_route_with_view_context(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, view_context=IDummy,
                         view_renderer=null_renderer)
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, IDummy, request_type)
        self.assertEqual(wrapper(None, None), 'OK')
        self._assertRoute(config, 'name', 'path')
        wrapper = self._getViewCallable(config, IOther, request_type)
        self.assertEqual(wrapper, None)

    def test_add_route_with_view_exception(self):
        from pyramid.renderers import null_renderer
        from zope.interface import implementedBy
        config = self._makeOne(autocommit=True)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, view_context=RuntimeError,
                         view_renderer=null_renderer)
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(
            config, ctx_iface=implementedBy(RuntimeError),
            request_iface=request_type, exception_view=True)
        self.assertEqual(wrapper(None, None), 'OK')
        self._assertRoute(config, 'name', 'path')
        wrapper = self._getViewCallable(
            config, ctx_iface=IOther,
            request_iface=request_type, exception_view=True)
        self.assertEqual(wrapper, None)

    def test_add_route_with_view_for(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, view_for=IDummy,
                         view_renderer=null_renderer)
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, IDummy, request_type)
        self.assertEqual(wrapper(None, None), 'OK')
        self._assertRoute(config, 'name', 'path')
        wrapper = self._getViewCallable(config, IOther, request_type)
        self.assertEqual(wrapper, None)

    def test_add_route_with_for_(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, for_=IDummy,
                         view_renderer=null_renderer)
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, IDummy, request_type)
        self.assertEqual(wrapper(None, None), 'OK')
        self._assertRoute(config, 'name', 'path')
        wrapper = self._getViewCallable(config, IOther, request_type)
        self.assertEqual(wrapper, None)

    def test_add_route_with_view_renderer(self):
        config = self._makeOne(autocommit=True)
        self._registerRenderer(config)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view,
                         view_renderer='files/minimal.txt')
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, None, request_type)
        self._assertRoute(config, 'name', 'path')
        self.assertEqual(wrapper(None, None).body, 'Hello!')

    def test_add_route_with_view_attr(self):
        from pyramid.renderers import null_renderer
        config = self._makeOne(autocommit=True)
        self._registerRenderer(config)
        class View(object):
            def __init__(self, context, request):
                pass
            def alt(self):
                return 'OK'
        config.add_route('name', 'path', view=View, view_attr='alt',
                         view_renderer=null_renderer)
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, None, request_type)
        self._assertRoute(config, 'name', 'path')
        request = self._makeRequest(config)
        self.assertEqual(wrapper(None, request), 'OK')

    def test_add_route_with_view_renderer_alias(self):
        config = self._makeOne(autocommit=True)
        self._registerRenderer(config)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view,
                         renderer='files/minimal.txt')
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, None, request_type)
        self._assertRoute(config, 'name', 'path')
        self.assertEqual(wrapper(None, None).body, 'Hello!')

    def test_add_route_with_view_permission(self):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        config = self._makeOne(autocommit=True)
        policy = lambda *arg: None
        config.registry.registerUtility(policy, IAuthenticationPolicy)
        config.registry.registerUtility(policy, IAuthorizationPolicy)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, view_permission='edit')
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, None, request_type)
        self._assertRoute(config, 'name', 'path')
        self.assertTrue(hasattr(wrapper, '__call_permissive__'))

    def test_add_route_with_view_permission_alias(self):
        from pyramid.interfaces import IAuthenticationPolicy
        from pyramid.interfaces import IAuthorizationPolicy
        config = self._makeOne(autocommit=True)
        policy = lambda *arg: None
        config.registry.registerUtility(policy, IAuthenticationPolicy)
        config.registry.registerUtility(policy, IAuthorizationPolicy)
        view = lambda *arg: 'OK'
        config.add_route('name', 'path', view=view, permission='edit')
        request_type = self._getRouteRequestIface(config, 'name')
        wrapper = self._getViewCallable(config, None, request_type)
        self._assertRoute(config, 'name', 'path')
        self.assertTrue(hasattr(wrapper, '__call_permissive__'))

    def test_conflict_route_with_view(self):
        from zope.configuration.config import ConfigurationConflictError
        config = self._makeOne()
        def view1(request): pass
        def view2(request): pass
        config.add_route('a', '/a', view=view1)
        config.add_route('a', '/a', view=view2)
        try:
            config.commit()
        except ConfigurationConflictError, why:
            c1, c2, c3, c4, c5, c6 = _conflictFunctions(why)
            self.assertEqual(c1, 'test_conflict_route_with_view')
            self.assertEqual(c2, 'test_conflict_route_with_view')
            self.assertEqual(c3, 'test_conflict_route_with_view')
            self.assertEqual(c4, 'test_conflict_route_with_view')
            self.assertEqual(c5, 'test_conflict_route_with_view')
            self.assertEqual(c6, 'test_conflict_route_with_view')
        else: # pragma: no cover
            raise AssertionError

class TestConfigurator_add_directive(unittest.TestCase):

    def setUp(self):
        from pyramid.config import Configurator
        self.config = Configurator()

    def test_extend_with_dotted_name(self):
        from pyramid.tests import test_config
        config = self.config
        config.add_directive(
            'dummy_extend', 'pyramid.tests.test_config.dummy_extend')
        self.assert_(hasattr(config, 'dummy_extend'))
        config.dummy_extend('discrim')
        context_after = config._ctx
        self.assertEqual(
            context_after.actions[-1][:3],
            ('discrim', None, test_config),
            )

    def test_extend_with_python_callable(self):
        from pyramid.tests import test_config
        config = self.config
        config.add_directive(
            'dummy_extend', dummy_extend)
        self.assert_(hasattr(config, 'dummy_extend'))
        config.dummy_extend('discrim')
        context_after = config._ctx
        self.assertEqual(
            context_after.actions[-1][:3],
            ('discrim', None, test_config),
            )

    def test_extend_same_name_doesnt_conflict(self):
        config = self.config
        config.add_directive(
            'dummy_extend', dummy_extend)
        config.add_directive(
            'dummy_extend', dummy_extend2)
        self.assert_(hasattr(config, 'dummy_extend'))
        config.dummy_extend('discrim')
        context_after = config._ctx
        self.assertEqual(
            context_after.actions[-1][:3],
            ('discrim', None, config.registry),
            )

    def test_extend_action_method_successful(self):
        from zope.configuration.config import ConfigurationConflictError
        config = self.config
        config.add_directive(
            'dummy_extend', dummy_extend)
        config.dummy_extend('discrim')
        config.dummy_extend('discrim')
        self.assertRaises(ConfigurationConflictError, config.commit)

    def test_directive_persists_across_configurator_creations(self):
        from zope.configuration.config import GroupingContextDecorator
        config = self.config
        config.add_directive('dummy_extend', dummy_extend)
        context = config._make_context(autocommit=False)
        context = GroupingContextDecorator(context)
        config2 = config.with_context(context)
        config2.dummy_extend('discrim')
        context_after = config2._ctx
        actions = context_after.actions
        self.assertEqual(len(actions), 1)
        self.assertEqual(
            context_after.actions[0][:3],
            ('discrim', None, config2.package),
            )

class TestPyramidConfigurationMachine(unittest.TestCase):
    def test_it(self):
        from pyramid.config import PyramidConfigurationMachine
        m = PyramidConfigurationMachine()
        self.assertEqual(m.autocommit, False)
        self.assertEqual(m.route_prefix, None)

class TestGlobalRegistriesIntegration(unittest.TestCase):
    def setUp(self):
        from pyramid.config import global_registries
        global_registries.empty()

    tearDown = setUp

    def _makeConfigurator(self, *arg, **kw):
        from pyramid.config import Configurator
        config = Configurator(*arg, **kw)
        return config

    def test_global_registries_empty(self):
        from pyramid.config import global_registries
        self.assertEqual(global_registries.last, None)

    def test_global_registries(self):
        from pyramid.config import global_registries
        config1 = self._makeConfigurator()
        config1.make_wsgi_app()
        self.assertEqual(global_registries.last, config1.registry)
        config2 = self._makeConfigurator()
        config2.make_wsgi_app()
        self.assertEqual(global_registries.last, config2.registry)
        self.assertEqual(list(global_registries),
                         [config1.registry, config2.registry])
        global_registries.remove(config2.registry)
        self.assertEqual(global_registries.last, config1.registry)


class DummyRequest:
    subpath = ()
    matchdict = None
    def __init__(self, environ=None):
        if environ is None:
            environ = {}
        self.environ = environ
        self.params = {}
        self.cookies = {}

class DummyResponse:
    status = '200 OK'
    headerlist = ()
    app_iter = ()
    body = ''

class DummyThreadLocalManager(object):
    pushed = None
    popped = False
    def push(self, d):
        self.pushed = d
    def pop(self):
        self.popped = True

from zope.interface import implements
class DummyEvent:
    implements(IDummy)

class DummyRegistry(object):
    def __init__(self, adaptation=None):
        self.utilities = []
        self.adapters = []
        self.adaptation = adaptation
    def subscribers(self, events, name):
        self.events = events
        return events
    def registerUtility(self, *arg, **kw):
        self.utilities.append((arg, kw))
    def registerAdapter(self, *arg, **kw):
        self.adapters.append((arg, kw))
    def queryAdapter(self, *arg, **kw):
        return self.adaptation

from pyramid.interfaces import IResponse
class DummyResponse(object):
    implements(IResponse)
    
from zope.interface import Interface
class IOther(Interface):
    pass

def _conflictFunctions(e):
    conflicts = e._conflicts.values()
    for conflict in conflicts:
        for confinst in conflict:
            yield confinst[2]
