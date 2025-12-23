"""
TP Bonus : Système de Livraison avec SPADE

"""
# MODIFICATION FINALE TP SPADE - Bothayn

import spade
import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
import logging

# Réduire les logs
logging.getLogger("spade").setLevel(logging.CRITICAL)
logging.getLogger("pyjabber").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# =============================================================================
# PARTIE 1 : Agent Livreur
# =============================================================================

class LivreurAgent(Agent):

    def __init__(self, jid, password, tarif, position, disponible=True):
        super().__init__(jid, password)
        self.tarif = tarif
        self.position = position
        self.disponible = disponible

    def calculer_distance(self, destination):
        return abs(self.position[0] - destination[0]) + abs(self.position[1] - destination[1])

    class RecevoirCFP(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            performative = msg.get_metadata("performative")

            # CFP
            if performative == "cfp":
                # body = "livraison:(3, 4)"
                contenu = msg.body.replace("livraison:", "")
                destination = eval(contenu)

                reply = Message(to=str(msg.sender))

                if self.agent.disponible:
                    distance = self.agent.calculer_distance(destination)
                    cout = distance * self.agent.tarif
                    reply.set_metadata("performative", "propose")
                    reply.body = f"cout:{cout}"
                    print(f"🚚 {self.agent.jid} propose {cout}")
                else:
                    reply.set_metadata("performative", "refuse")
                    reply.body = "indisponible"
                    print(f"🚫 {self.agent.jid} refuse (indisponible)")

                await self.send(reply)

            elif performative == "accept-proposal":
                print(f"✅ {self.agent.jid} : Livraison acceptée !")
                reply = Message(to=str(msg.sender))
                reply.set_metadata("performative", "inform")
                reply.body = "done"
                await self.send(reply)

            elif performative == "reject-proposal":
                print(f"❌ {self.agent.jid} : Offre refusée")

    async def setup(self):
        print(f"🚚 {self.jid} démarré | tarif={self.tarif} | position={self.position}")
        self.add_behaviour(self.RecevoirCFP())

# =============================================================================
# PARTIE 2 : Agent Gestionnaire
# =============================================================================

class GestionnaireAgent(Agent):

    def __init__(self, jid, password, livreurs_jids):
        super().__init__(jid, password)
        self.livreurs_jids = livreurs_jids
        self.propositions = []

    class LancerAppelOffres(OneShotBehaviour):

        async def run(self):
            print(f"\n📢 Appel d'offres pour livraison à {self.agent.destination}")

            for livreur in self.agent.livreurs_jids:
                msg = Message(to=livreur)
                msg.set_metadata("performative", "cfp")
                msg.body = f"livraison:{self.agent.destination}"
                await self.send(msg)

    class CollecterPropositions(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            performative = msg.get_metadata("performative")

            if performative == "propose":
                cout = float(msg.body.replace("cout:", ""))
                self.agent.propositions.append({
                    "livreur": str(msg.sender),
                    "cout": cout
                })
                print(f"📥 Proposition reçue de {msg.sender} : {cout}")

            elif performative == "refuse":
                print(f"🚫 {msg.sender} a refusé")

            elif performative == "inform" and msg.body == "done":
                print(f"📦 Livraison confirmée par {msg.sender}")

    class SelectionnerMeilleur(OneShotBehaviour):

        async def run(self):
            await asyncio.sleep(3)

            print(f"\n🔍 Analyse des propositions ({len(self.agent.propositions)})")

            if not self.agent.propositions:
                print("❌ Aucune proposition reçue")
                return

            meilleur = min(self.agent.propositions, key=lambda p: p["cout"])
            gagnant = meilleur["livreur"]

            print(f"🏆 Gagnant : {gagnant} avec coût {meilleur['cout']}")

            for prop in self.agent.propositions:
                msg = Message(to=prop["livreur"])
                if prop["livreur"] == gagnant:
                    msg.set_metadata("performative", "accept-proposal")
                else:
                    msg.set_metadata("performative", "reject-proposal")
                await self.send(msg)

    async def setup(self):
        print(f"📋 {self.jid} démarré")
        self.add_behaviour(self.CollecterPropositions())

    def lancer_livraison(self, destination):
        self.destination = destination
        self.propositions = []
        self.add_behaviour(self.LancerAppelOffres())
        self.add_behaviour(self.SelectionnerMeilleur())

# =============================================================================
# PARTIE 3 : main()
# =============================================================================

async def main():

    print("\n🚚 SIMULATION SYSTÈME DE LIVRAISON\n")

    livreur_a = LivreurAgent("livreur_a@localhost", "password", 2.0, (0, 0), True)
    livreur_b = LivreurAgent("livreur_b@localhost", "password", 1.5, (5, 5), True)
    livreur_c = LivreurAgent("livreur_c@localhost", "password", 1.0, (10, 0), False)

    gestionnaire = GestionnaireAgent(
        "gestionnaire@localhost",
        "password",
        [
            "livreur_a@localhost",
            "livreur_b@localhost",
            "livreur_c@localhost"
        ]
    )

    await livreur_a.start()
    await livreur_b.start()
    await livreur_c.start()
    await gestionnaire.start()

    await asyncio.sleep(2)

    gestionnaire.lancer_livraison((3, 4))

    await asyncio.sleep(10)

    await livreur_a.stop()
    await livreur_b.stop()
    await livreur_c.stop()
    await gestionnaire.stop()

    print("\n✅ SIMULATION TERMINÉE\n")

if __name__ == "__main__":
    spade.run(main(), embedded_xmpp_server=True)