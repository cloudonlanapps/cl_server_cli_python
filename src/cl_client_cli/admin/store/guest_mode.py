import asyncio
import click
from pydantic import BaseModel
from ... import common
from ...store import get_store_manager

@click.command("get-guest-mode")
@click.pass_context
def store_get_guest_mode(ctx: click.Context):
    """Get store guest mode configuration (admin only).

    Examples:
        cl-client admin store get-guest-mode
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.get_pref()

                if result.is_error or result.data is None:
                    common.output_error(
                        ctx, str(result.error) if result.is_error else "No data returned"
                    )

                # Create simple response with just guest_mode
                class GuestModeResponse(BaseModel):
                    guest_mode: bool
                    service: str = "store"

                guest_mode_data = GuestModeResponse(guest_mode=result.data.guest_mode)
                common.output_sdk_result(ctx, guest_mode_data)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())

@click.command("set-guest-mode")
@click.argument("enabled", type=bool)
@click.pass_context
def store_set_guest_mode(ctx: click.Context, enabled: bool):
    """Enable or disable guest mode for store (admin only).

    Guest mode allows unauthenticated access to the store service.

    Examples:
        cl-client admin store set-guest-mode true
        cl-client admin store set-guest-mode false
    """

    async def run():
        async with await get_store_manager(ctx) as manager:
            try:
                result = await manager.update_guest_mode(enabled)

                if result.is_error:
                    common.output_error(ctx, str(result.error))

                # Output success response for void operation
                success = common.SuccessResponse(
                    message=f"Store guest mode {'enabled' if enabled else 'disabled'}"
                )
                common.output_sdk_result(ctx, success)
            finally:
                context: common.CLIContext = ctx.obj
                if context.session:
                    await context.session.close()

    asyncio.run(run())
