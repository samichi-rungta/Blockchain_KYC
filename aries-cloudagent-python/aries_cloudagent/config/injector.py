"""Standard Injector implementation."""

from typing import Dict, Mapping, Optional, Type

from .base import BaseInjector, BaseProvider, InjectionError, InjectType
from .provider import CachedProvider, InstanceProvider
from .settings import Settings


class Injector(BaseInjector):
    """Injector implementation with static and dynamic bindings."""

    def __init__(
        self,
        settings: Optional[Mapping[str, object]] = None,
        *,
        enforce_typing: bool = True,
    ):
        """Initialize an `Injector`."""
        self.enforce_typing = enforce_typing
        self._providers: Dict[Type, BaseProvider] = {}
        self._settings = Settings(settings)

    @property
    def settings(self) -> Settings:
        """Accessor for scope-specific settings."""
        return self._settings

    @settings.setter
    def settings(self, settings: Settings):
        """Setter for scope-specific settings."""
        self._settings = settings

    def bind_instance(self, base_cls: Type[InjectType], instance: InjectType):
        """Add a static instance as a class binding."""
        self._providers[base_cls] = InstanceProvider(instance)

    def bind_provider(
        self, base_cls: Type[InjectType], provider: BaseProvider, *, cache: bool = False
    ):
        """Add a dynamic instance resolver as a class binding."""
        if not provider:
            raise ValueError("Class provider binding must be non-empty")
        if cache and not isinstance(provider, CachedProvider):
            provider = CachedProvider(provider)
        self._providers[base_cls] = provider

    def soft_bind_instance(self, base_cls: Type[InjectType], instance: InjectType):
        """Add a static instance as a soft class binding.

        The binding occurs only if a provider for the same type does not already exist.
        """
        if not self.get_provider(base_cls):
            self.bind_instance(base_cls, instance)

    def soft_bind_provider(
        self, base_cls: Type[InjectType], provider: BaseProvider, *, cache: bool = False
    ):
        """Add a dynamic instance resolver as a soft class binding.

        The binding occurs only if a provider for the same type does not already exist.
        """
        if not self.get_provider(base_cls):
            self.bind_provider(base_cls, provider, cache=cache)

    def clear_binding(self, base_cls: Type[InjectType]):
        """Remove a previously-added binding."""
        if base_cls in self._providers:
            del self._providers[base_cls]

    def get_provider(self, base_cls: Type[InjectType]):
        """Find the provider associated with a class binding."""
        return self._providers.get(base_cls)

    def inject_or(
        self,
        base_cls: Type[InjectType],
        settings: Optional[Mapping[str, object]] = None,
        default: Optional[InjectType] = None,
    ) -> Optional[InjectType]:
        """Get the provided instance of a given class identifier or default if not found.

        Args:
            base_cls: The base class to retrieve an instance of
            settings: An optional dict providing configuration to the provider
            default: default return value if no instance is found

        Returns:
            An instance of the base class, or None

        """
        if not base_cls:
            raise InjectionError("No base class provided for lookup")
        provider = self._providers.get(base_cls)
        if settings:
            ext_settings = self.settings.extend(settings)
        else:
            ext_settings = self.settings
        if provider:
            result = provider.provide(ext_settings, self)
        else:
            result = None

        if result and not isinstance(result, base_cls) and self.enforce_typing:
            raise InjectionError(
                "Provided instance does not implement the base class: {}".format(
                    base_cls.__name__
                )
            )

        return result if result is not None else default

    def inject(
        self,
        base_cls: Type[InjectType],
        settings: Optional[Mapping[str, object]] = None,
    ) -> InjectType:
        """Get the provided instance of a given class identifier.

        Args:
            base_cls (Type[InjectType]): The base class to retrieve an instance of.
            settings (Optional[Mapping[str, object]]): An optional dictionary providing
                configuration to the provider.

        Returns:
            InjectType: An instance of the base class, or None.

        Raises:
            InjectionError: If no instance is provided for the given class identifier.

        """
        result = self.inject_or(base_cls, settings)
        if result is None:
            raise InjectionError(
                "No instance provided for class: {}".format(base_cls.__name__)
            )
        return result

    def copy(self) -> BaseInjector:
        """Produce a copy of the injector instance."""
        result = Injector(self.settings)
        result.enforce_typing = self.enforce_typing
        result._providers = self._providers.copy()
        return result

    def __repr__(self) -> str:
        """Provide a human readable representation of this object."""
        return f"<{self.__class__.__name__}>"
