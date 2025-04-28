from tortoise.transactions import in_transaction
from Database_and_ORM.Database_Models import User
INITIAL_USER_NUMBER = 500000
INCREMENT_STEP = 11

async def get_next_user_number():
    async with in_transaction():
        last_user = await User.all().order_by('-user_number').first()
        if last_user and last_user.user_number:
            return last_user.user_number + INCREMENT_STEP
        else:
            return INITIAL_USER_NUMBER + INCREMENT_STEP
