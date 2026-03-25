#!/usr/bin/env python
import warnings

from datetime import datetime

try:
    # Works when executed as a module from project root.
    from complianceguard.chain import ComplianceGuardChain
except ModuleNotFoundError:
    # Works when executed directly from the complianceguard folder.
    from chain import ComplianceGuardChain

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")


def run():
    """
    Run the compliance research chain.
    """
    query = 'Quels sont les documents requis pour l obtention du congé startup ?'
    current_year = str(datetime.now().year)

    try:
        chain = ComplianceGuardChain()
        result = chain.run(query=query, current_year=current_year)
        print("\n" + "=" * 60)
        print("RÉSULTAT:")
        print("=" * 60)
        print(result)
    except Exception as e:
        raise Exception(f"An error occurred while running the chain: {e}")


if __name__ == "__main__":
    run()
