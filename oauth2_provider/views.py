import logging

from django.views.generic import FormView
from django.http import HttpResponseBadRequest
from oauthlib.common import urlencode
from oauthlib.oauth2 import Server
from oauthlib.oauth2 import errors

from .oauth2_validators import OAuth2Validator
from .models import Application
from .forms import AllowForm


log = logging.getLogger('oauth2_provider')
server = Server(OAuth2Validator())


class AuthorizationCodeView(FormView):
    template_name = 'oauth2_provider/authorize.html'
    form_class = AllowForm
    success_url = '/fixme/'

    def _extract_params(self, request):
        log.debug('Extracting parameters from request.')
        uri = request.build_absolute_uri()
        http_method = request.method
        headers = request.META
        if 'wsgi.input' in headers:
            del headers['wsgi.input']
        if 'wsgi.errors' in headers:
            del headers['wsgi.errors']
        if 'HTTP_AUTHORIZATION' in headers:
            headers['Authorization'] = headers['HTTP_AUTHORIZATION']
        body = urlencode(request.POST.items())
        return uri, http_method, body, headers

    def get_context_data(self, **kwargs):
        context = super(AuthorizationCodeView, self).get_context_data(**kwargs)
        return context

    def get(self, request, *args, **kwargs):
        uri, http_method, body, headers = self._extract_params(request)
        redirect_uri = request.GET.get('redirect_uri', None)
        try:
            scopes, credentials = server.validate_authorization_request(uri, http_method, body, headers)
            log.debug('Saving credentials to session, %r.', credentials)
            request.session['oauth2_credentials'] = credentials
            kwargs['scopes'] = scopes
            kwargs['redirect_uri'] = redirect_uri
            # at this point we know an Application instance with such client_id exists in the database
            kwargs['application'] = Application.objects.get(client_id=credentials['client_id'])
            kwargs.update(credentials)
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            kwargs['form'] = form
            return self.render_to_response(self.get_context_data(**kwargs))

        except errors.FatalClientError as e:
            log.debug('Fatal client error, should redirecting to error page.')
            return HttpResponseBadRequest()

    def form_valid(self, form):
        if form.cleaned_data['allow']:
            log.debug('Application allowed')
        return super(AuthorizationCodeView, self).form_valid(form)
