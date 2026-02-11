import asyncio
import click
from pydantic import BaseModel
from ... import common

@click.group("guest-mode")
def guest_mode():
    """Compute guest mode configuration (admin only)."""
    pass

class GuestModeResponse(BaseModel):
    guest_mode: bool
    service: str = "compute"

@guest_mode.command("get")
@click.pass_context
def get_guest_mode(ctx: click.Context):
    """Get compute guest mode configuration.

    Examples:
        cl-client admin compute guest-mode get
    """

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            client = session.create_compute_client()
            enabled = await client.get_guest_mode()
            common.output_sdk_result(ctx, GuestModeResponse(guest_mode=enabled))
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            context: common.CLIContext = ctx.obj
            if context.session:
                await context.session.close()

    asyncio.run(run())

@guest_mode.command("set")
@click.argument("enabled", type=bool)
@click.pass_context
def set_guest_mode(ctx: click.Context, enabled: bool):
    """Enable or disable guest mode for compute.

    Examples:
        cl-client admin compute guest-mode set true
        cl-client admin compute guest-mode set false
    """

    async def run():
        session = await common.get_session_manager(ctx)
        try:
            client = session.create_compute_client()
            await client.update_guest_mode(enabled)
            common.output_sdk_result(
                ctx, 
                common.SuccessResponse(message=f"Compute guest mode set to {enabled}")
            )
        except Exception as e:
            common.output_error(ctx, str(e))
        finally:
            await session.close()

    asyncio.run(run())
