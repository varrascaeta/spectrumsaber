# Strawberry imports
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension
# GQL Auth imports
from gqlauth.user.queries import UserQueries
from gqlauth.core.middlewares import JwtSchema
from gqlauth.user import arg_mutations as mutations
# Project imports
from src.campaigns.schema import CampaignQuery


@strawberry.type
class Query(UserQueries, CampaignQuery):
    pass


@strawberry.type
class Mutation:
    verify_token = mutations.VerifyToken.field
    update_account = mutations.UpdateAccount.field
    archive_account = mutations.ArchiveAccount.field
    delete_account = mutations.DeleteAccount.field
    password_change = mutations.PasswordChange.field
    token_auth = mutations.ObtainJSONWebToken.field
    register = mutations.Register.field
    verify_account = mutations.VerifyAccount.field
    resend_activation_email = mutations.ResendActivationEmail.field
    send_password_reset_email = mutations.SendPasswordResetEmail.field
    password_reset = mutations.PasswordReset.field
    password_set = mutations.PasswordSet.field
    refresh_token = mutations.RefreshToken.field
    revoke_token = mutations.RevokeToken.field


# This is essentially the same as strawberries schema though it
# injects the user to `info.context["request"].user`
schema = JwtSchema(
    query=Query,
    mutation=Mutation,
    extensions=[
        DjangoOptimizerExtension,
    ]
)
