from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    ForeignKey,
    func,
)
from sqlalchemy.orm import relationship
from datetime import date, datetime, timedelta
from config.config import SOURCE_DIR
from models.base import Base
from services.db import engine, get_db_session
import pandas as pd


class Fixture(Base):
    __tablename__ = "fixtures"

    league = relationship("League", back_populates="fixture")
    season = relationship("Season", back_populates="fixture")

    def __repr__(self):
        """Return a string representation of the User object."""
        return (
            f"<Fixture(fixture_id={self.fixture_id}, league_id={self.league_id}, season_id={self.season_id},"
            f"country_name={self.country_name}, season_year={self.season_year}, league_name={self.league_name},"
            f"round={self.round}, date={self.date}, status={self.status}, referee={self.referee},"
            f"home_team_id={self.home_team_id}, home_team_name={self.home_team_name},"
            f"away_team_id={self.away_team_id}, away_team_name={self.away_team_name},"
            f"goals_home={self.goals_home}, goals_away={self.goals_away})>"
            f"goals_home_ht={self.goals_home}, goals_away_ht={self.goals_away})>"
        )

    fixture_id = Column(Integer, primary_key=True)
    league_id = Column(Integer, ForeignKey("leagues.league_id"), nullable=False)
    season_id = Column(String, ForeignKey("seasons.season_id"), nullable=False)
    country_name = Column(String, nullable=False)
    season_year = Column(String, nullable=False)
    league_name = Column(String, nullable=False)
    round = Column(String)
    date = Column(Date)
    status = Column(String)
    referee = Column(String)
    home_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    home_team_name = Column(String, nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.team_id"), nullable=False)
    away_team_name = Column(String, nullable=False)
    goals_home = Column(Integer)
    goals_away = Column(Integer)
    goals_home_ht = Column(Integer)
    goals_away_ht = Column(Integer)

    home_team = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_team"
    )
    away_team = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_team"
    )

    @classmethod
    def get_results_max_date(cls):
        session = get_db_session()
        try:
            max_date = (
                session.query(func.max(cls.date)).filter(cls.status == "FT").scalar()
            )
            return max_date.strftime("%Y-%m-%d")
        except Exception as e:
            raise Exception
        finally:
            session.close()

    @classmethod
    def get_today_fixtures(cls):
        session = get_db_session()
        try:
            today_fixtures_df = pd.read_sql_query(
                session.query(cls).filter(cls.date == date.today()).statement, engine
            )
            return today_fixtures_df
        except Exception as e:
            raise Exception
        finally:
            session.close()

    @classmethod
    def get_all_fixtures_by_team(cls, team_id):
        session = get_db_session()
        try:
            team_fixtures_df = pd.read_sql_query(
                session.query(cls)
                .filter((cls.home_team_id == team_id) | (cls.away_team_id == team_id))
                .statement,
                engine,
            )
            return team_fixtures_df
        except Exception as e:
            raise Exception
        finally:
            session.close()

    @classmethod
    def get_season_fixtures_by_team(cls, team_id: int, season_year: str):
        session = get_db_session()
        try:
            team_fixtures_df = pd.read_sql_query(
                session.query(cls)
                .filter(
                    (cls.season_year == season_year)
                    & ((cls.home_team_id == team_id) | (cls.away_team_id == team_id))
                )
                .statement,
                engine,
            )
            return team_fixtures_df
        except Exception as e:
            raise Exception
        finally:
            session.close()

    @classmethod
    def get_season_results_by_team(cls, team_id, season_year):
        session = get_db_session()
        try:
            team_results_df = pd.read_sql_query(
                session.query(cls)
                .filter(
                    (cls.status == "FT")
                    & (cls.season_year == season_year)
                    & ((cls.home_team_id == team_id) | (cls.away_team_id == team_id))
                )
                .statement,
                engine,
            )
            return team_results_df
        except Exception as e:
            raise Exception
        finally:
            session.close()

    # Get all or part of fixtures to create a table
    @staticmethod
    def filter_fixtures_by_rounds(df, rounds):
        match rounds:
            case "all_finished":
                return df[df["fixture.status.short"] == "FT"]
            case "last_5":
                # TODO: think if it make sense to build table for last 5 when there are Relegation/Playoff rounds
                return None
            case int():
                # If rounds is a number filter only "Regular Season" fixtures
                df = df[df["league.round"].str.contains("Regular Season")]
                return df[
                    df["league.round"].str.split("-").str[1].str.strip().astype(int)
                    <= rounds
                ]

    @classmethod
    def get_season_stats_by_team(cls, team_id, season_year):
        session = get_db_session()
        try:
            team_results_df = pd.read_sql_query(
                session.query(cls)
                .filter(
                    (cls.status == "FT")
                    & (cls.season_year == season_year)
                    & ((cls.home_team_id == team_id) | (cls.away_team_id == team_id))
                )
                .statement,
                engine,
            )
        except Exception as e:
            print(f"Error: {e}")
            raise Exception
        finally:
            session.close()

        # Apply aggregations
        team_results_df["team_group"] = team_results_df.apply(
            lambda row: "home" if row["home_team_id"] == team_id else "away", axis=1
        )
        team_results_df["team_name"] = team_results_df.apply(
            lambda row: (
                row["home_team_name"]
                if row["team_group"] == "home"
                else row["away_team_name"]
            ),
            axis=1,
        )
        team_results_df = team_results_df.sort_values(by="date")

        # Add 'form' column to the DataFrame
        team_results_df["form"] = team_results_df.apply(
            lambda row: (
                "W"
                if (
                    row["team_group"] == "home"
                    and row["goals_home"] > row["goals_away"]
                )
                or (
                    row["team_group"] == "away"
                    and row["goals_away"] > row["goals_home"]
                )
                else "D" if row["goals_home"] == row["goals_away"] else "L"
            ),
            axis=1,
        )
        team_stats = (
            team_results_df.groupby(["team_group", "team_name"])
            .agg(
                games=("fixture_id", "count"),
                wins=("form", lambda x: (x == "W").sum()),
                draws=("form", lambda x: (x == "D").sum()),
                loses=("form", lambda x: (x == "L").sum()),
                goals_scored=("goals_home", "sum"),
                goals_conceded=("goals_away", "sum"),
                avg_goals_scored=("goals_home", lambda x: round(x.mean(), 2)),
                avg_goals_conceded=("goals_away", lambda x: round(x.mean(), 2)),
                form=("form", lambda x: "".join(x)),
            )
            .reset_index()
        )

        return team_stats

    @classmethod
    def create_game_preview(cls, home_team_id, away_team_id):
        home_stats = cls.get_season_stats_by_team(home_team_id, "2023")
        away_stats = cls.get_season_stats_by_team(away_team_id, "2023")
        game_preview_df = pd.concat([home_stats, away_stats])
        game_preview_df.to_csv(
            f"{SOURCE_DIR}/previews/{home_team_id}-{away_team_id}.csv",
            index=False,
        )
        return game_preview_df

    @classmethod
    def get_dates_to_update(cls):
        session = get_db_session()
        curr_date = datetime.now().date()
        # Search min(date) for Not Started games
        min_date_to_pull = (
            session.query(func.min(cls.date))
            .filter((cls.status == "NS") & (cls.season_year == "2023"))
            .scalar()
        )
        # Generate a list of dates between min_date_to_pull and curr_date
        date_range = [
            min_date_to_pull + timedelta(days=x)
            for x in range((curr_date - min_date_to_pull).days + 1)
        ]
        # Convert dates to string format
        date_strings = [single_date.strftime("%Y-%m-%d") for single_date in date_range]
        return date_strings

    @classmethod
    def update(cls, df: pd.DataFrame):
        session = get_db_session()
        try:
            # Convert DataFrame to list of dictionaries and update all rows into the database table using the session
            data = df.to_dict(orient="records")
            # Filter out rows for which fixture_id does not exist in the database
            existing_fixture_ids = [row["fixture_id"] for row in data]
            existing_fixture_ids_in_db = [
                row[0]
                for row in session.query(cls.fixture_id)
                .filter(cls.fixture_id.in_(existing_fixture_ids))
                .all()
            ]
            data_to_update = [
                row for row in data if row["fixture_id"] in existing_fixture_ids_in_db
            ]
            session.bulk_update_mappings(cls, data_to_update)
            session.commit()
            print(f"{cls.__name__} data updated successfully!")
        except Exception as e:
            # Rollback the session in case of an error to discard the changes
            session.rollback()
            print(f"Error while updating {cls.__name__} data: {e}")
        finally:
            session.close()

    @classmethod
    def get_overcome_games(cls):
        overcome_mask = (
            (cls.goals_home_ht > cls.goals_away_ht) & (cls.goals_home < cls.goals_away)
        ) | (
            (cls.goals_home_ht < cls.goals_away_ht) & (cls.goals_home > cls.goals_away)
        )

        session = get_db_session()
        try:
            overcome_games_df = pd.read_sql_query(
                session.query(cls).filter(overcome_mask).statement, engine
            )
            return overcome_games_df
        except Exception as e:
            # Rollback the session in case of an error to discard the changes
            session.rollback()
            print(f"Error while updating {cls.__name__} data: {e}")
        finally:
            session.close()
