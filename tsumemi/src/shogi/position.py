from __future__ import annotations

import re

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tsumemi.src.shogi.basetypes import Move

from tsumemi.src.shogi.basetypes import Koma, KomaType, Side, Square
from tsumemi.src.shogi.basetypes import KOMA_FROM_SFEN
from tsumemi.src.shogi.position_internals import BoardRepresentation, HandRepresentation

class Position:
    """Represents a shogi position, including board position, side to
    move, and pieces in hand.
    """
    def __init__(self) -> None:
        self.board_representation = BoardRepresentation()
        self.hand_sente = HandRepresentation()
        self.hand_gote = HandRepresentation()
        self.turn = Side.SENTE
        self.movenum = 1
        return
    
    def __str__(self) -> str:
        elems = [
            str(self.board_representation),
            "Sente hand:", str(self.hand_sente),
            "Gote hand:", str(self.hand_gote),
            "Turn: Sente" if self.turn == Side.SENTE else "Turn: Gote"
        ]
        return "\n".join(elems)
    
    def reset(self) -> None:
        self.board_representation.reset()
        self.hand_sente.reset()
        self.hand_gote.reset()
        self.turn = Side.SENTE
        self.movenum = 1
        return
    
    def get_hand_of_side(self, side: Side) -> HandRepresentation:
        return self.hand_sente if side is Side.SENTE else self.hand_gote
    
    def set_hand_koma_count(self,
            side: Side,
            ktype: KomaType,
            count: int
        ) -> None:
        hand = self.get_hand_of_side(side)
        hand.set_komatype_count(ktype, count)
        return
    
    def inc_hand_koma(self, side: Side, ktype: KomaType) -> None:
        hand = self.get_hand_of_side(side)
        hand.inc_komatype(ktype)
        return
    
    def dec_hand_koma(self, side: Side, ktype: KomaType) -> None:
        hand = self.get_hand_of_side(side)
        hand.dec_komatype(ktype)
        return
    
    def is_hand_empty(self, side: Side) -> bool:
        return self.get_hand_of_side(side).is_empty()
    
    def set_koma(self, koma: Koma, sq: Square) -> None:
        return self.board_representation.set_koma(koma, sq)
    
    def get_koma(self, sq: Square) -> Koma:
        return self.board_representation.get_koma(sq)
    
    def create_move(self,
            sq1: Square, 
            sq2: Square,
            is_promotion: bool = False
        ) -> Move:
        """Creates a move from two squares. Move need not necessarily
        be legal or even valid.
        """
        return Move(
            start_sq=sq1,
            end_sq=sq2,
            is_promotion=is_promotion,
            koma=self.get_koma(sq1),
            captured=self.get_koma(sq2)
        )
    
    def make_move(self, move: Move) -> None:
        """Makes a move on the board.
        """
        if move.is_pass():
            # to account for game terminations or other passing moves
            self.movenum += 1
            return
        elif move.is_drop:
            self.dec_hand_koma(move.side, KomaType.get(move.koma))
            self.set_koma(move.koma, move.end_sq)
            self.turn = self.turn.switch()
            self.movenum += 1
            return
        else:
            self.set_koma(Koma.NONE, move.start_sq)
            if move.captured != Koma.NONE:
                self.inc_hand_koma(
                    move.side,
                    KomaType.get(move.captured).unpromote()
                )
            self.set_koma(
                move.koma.promote() if move.is_promotion else move.koma,
                move.end_sq
            )
            self.turn = self.turn.switch()
            self.movenum += 1
            return
    
    def unmake_move(self, move: Move) -> None:
        """Unplays/retracts a move from the board.
        """
        if move.is_pass():
            self.movenum -= 1
            return
        elif move.is_drop:
            self.set_koma(Koma.NONE, move.end_sq)
            self.inc_hand_koma(move.side, KomaType.get(move.koma))
            self.turn = self.turn.switch()
            self.movenum -= 1
            return
        else:
            if move.captured != Koma.NONE:
                self.dec_hand_koma(
                    move.side,
                    KomaType.get(move.captured).unpromote()
                )
            self.set_koma(move.captured, move.end_sq)
            self.set_koma(move.koma, move.start_sq)
            self.turn = self.turn.switch()
            self.movenum -= 1
            return
    
    def _set_koma_from_sfen(self,
            ch: str, 
            col_num: int,
            row_num: int,
            promotion_flag: bool
        ) -> None:
        try:
            koma = KOMA_FROM_SFEN[ch]
        except KeyError:
            raise ValueError(f"SFEN contains unknown character '{ch}'")
        sq = Square.from_cr(col_num=col_num, row_num=row_num)
        if promotion_flag:
            koma = koma.promote()
        self.set_koma(koma, sq)
        return
    
    def _parse_sfen_board(self, sfen_board: str) -> None:
        # Parses the part of an SFEN string representing the board.
        rows = sfen_board.split("/")
        if len(rows) != 9:
            raise ValueError("SFEN board has wrong number of rows")
        for i, row in enumerate(rows):
            col_num = 9
            promotion_flag = False
            for ch in row:
                if col_num <= 0:
                    raise ValueError("SFEN row has wrong length")
                if ch.isdigit():
                    if promotion_flag:
                        raise ValueError("Digit cannot follow + in SFEN")
                    col_num -= int(ch)
                    continue
                elif ch == "+":
                    if promotion_flag:
                        raise ValueError("+ cannot follow + in SFEN")
                    promotion_flag = True
                    continue
                else:
                    # This line has the intended side effects
                    self._set_koma_from_sfen(
                        ch, col_num, i+1, promotion_flag
                    )
                    promotion_flag = False
                    col_num -= 1
            else: # for-else loop over row
                if col_num != 0:
                    raise ValueError("SFEN row has wrong length")
                if promotion_flag:
                    raise ValueError("SFEN row cannot end with +")
        return
    
    def _parse_sfen_hands(self, sfen_hands: str) -> None:
        it_hands = re.findall(r"(\d*)([plnsgbrPLNSGBR])", sfen_hands)
        for ch_count, ch in it_hands:
            try:
                koma = KOMA_FROM_SFEN[ch]
            except KeyError:
                raise ValueError(f"SFEN contains unknown character '{ch}'")
            ktype = KomaType.get(koma)
            target_hand = self.hand_sente if ch.isupper() else self.hand_gote
            count = int(ch_count) if ch_count else 1
            target_hand.set_komatype_count(ktype, count)
        return
    
    def from_sfen(self, sfen: str) -> None:
        """Parse an SFEN string and set up the position it represents.
        """
        sfen_board, sfen_turn, sfen_hands, sfen_move_num = sfen.split(" ")
        self.reset()
        if sfen_turn == "b":
            self.turn = Side.SENTE
        elif sfen_turn == "w":
            self.turn = Side.GOTE
        else:
            # This is possibly too strict
            raise ValueError("SFEN contains unknown side to move")
        try:
            self.movenum = int(sfen_move_num)
        except ValueError:
            raise ValueError(
                f"SFEN contains unknown movenumber '{sfen_move_num}'"
            )
        try:
            self._parse_sfen_board(sfen_board)
            self._parse_sfen_hands(sfen_hands)
        except ValueError as e:
            raise ValueError(f"Invalid SFEN: '{sfen}'") from e
        return
    
    def to_sfen(self) -> str:
        """Return SFEN string representing the current position.
        """
        sfen_board = self.board_representation.to_sfen()
        sfen_turn = "b" if self.turn is Side.SENTE else "w"
        if self.hand_sente.is_empty() and self.hand_gote.is_empty():
            sfen_hands = "-"
        else:
            sfen_hands = "".join((
                self.hand_sente.to_sfen(),
                self.hand_gote.to_sfen().lower()
            ))
        sfen_move_num = str(self.movenum)
        return " ".join((sfen_board, sfen_turn, sfen_hands, sfen_move_num))