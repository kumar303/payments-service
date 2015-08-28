from nose.tools import eq_
from requests.exceptions import HTTPError

from payments_service.base.tests import FormTest

from ..forms import SignInForm
from .test_views import BaseSignInTest


class TestSignInForm(BaseSignInTest, FormTest):

    def submit(self, data=None):
        if data is None:
            data = {'access_token': self.access_token}
        return SignInForm(data)

    def test_missing_token_or_code(self):
        form = self.submit(data={})
        self.assert_form_error(
            form.errors, '__all__',
            msg='access_token or authorization_code is required')

    def test_bad_fxa_response(self):
        self.set_fxa_post_side_effect(HTTPError('Bad Request'))

        form = self.submit()
        self.assert_form_error(form.errors, 'access_token',
                               msg='invalid FxA response')
        assert self.fxa_post.called

    def test_missing_scope(self):
        self.set_fxa_verify_response(scope=[])
        form = self.submit()
        self.assert_form_error(form.errors, 'access_token',
                               msg='.*missing the payments scope')
        assert self.fxa_post.called

    def test_missing_email_scope(self):
        self.set_fxa_verify_response(scope=['payments'])
        form = self.submit()
        self.assert_form_error(form.errors, 'access_token',
                               msg='.*missing the profile:email scope')
        assert self.fxa_post.called

    def test_honor_full_profile_access(self):
        self.set_fxa_verify_response(scope=['payments', 'profile'])
        assert self.submit().is_valid()

    def test_form_ok(self):
        self.set_fxa_verify_response()
        form = self.submit()
        assert form.is_valid(), form.errors.as_text()

        eq_(form.fxa_user_id, self.fxa_user_id)
        eq_(form.fxa_email, self.fxa_email)

        assert self.fxa_post.called


class TestSignInFormWithCode(BaseSignInTest, FormTest):

    def setUp(self):
        super(TestSignInFormWithCode, self).setUp()
        self.code = 'fxa-auth-code'

    def submit(self, data=None):
        if data is None:
            data = {'authorization_code': self.code,
                    'client_id': self.client_id}
        return SignInForm(data)

    def test_form_ok(self):
        self.set_fxa_token_response()
        self.set_fxa_verify_response()

        form = self.submit()
        assert form.is_valid(), form.errors.as_text()

        eq_(form.fxa_user_id, self.fxa_user_id)
        eq_(form.fxa_email, self.fxa_email)

        assert self.fxa_post.called

    def test_missing_client_id(self):
        form = self.submit(data={'authorization_code': self.code})
        self.assert_form_error(form.errors, '__all__',
                               msg='client_id is required')

    def test_wrong_client_id(self):
        form = self.submit(data={'authorization_code': self.code,
                                 'client_id': 'nope'})
        assert 'client_id' in form.errors, form.errors.as_text()

    def test_bad_token_response(self):
        self.set_fxa_post_side_effect(HTTPError('Bad Request'))

        form = self.submit()
        self.assert_form_error(form.errors, '__all__',
                               msg='invalid FxA response')
        assert self.fxa_post.called

    def test_token_is_verified(self):
        self.set_fxa_token_response()
        # Set up a scope with a missing email just as a smoke test to make
        # sure the token is validated.
        self.set_fxa_verify_response(scope=['payments'])
        form = self.submit()

        self.assert_form_error(form.errors, '__all__')
        # Make sure token was validated:
        assert self.fxa_post.called
