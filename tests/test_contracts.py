from ivy.interfaces import contracts


def test_contracts_expose_expected_protocols() -> None:
    names = {
        "ContextResolver",
        "ConfigResolver",
        "ArtifactCatalog",
        "SelectorEngine",
        "PlanBuilder",
        "ApplyEngine",
        "StateStore",
        "GitGateway",
    }
    for name in names:
        assert hasattr(contracts, name)


def test_git_gateway_contract_methods_exist() -> None:
    protocol = contracts.GitGateway
    assert hasattr(protocol, "status_clean")
    assert hasattr(protocol, "pull_ff_only")
    assert hasattr(protocol, "push")

