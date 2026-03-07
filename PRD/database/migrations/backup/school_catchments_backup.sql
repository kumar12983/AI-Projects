/**** CHANGE DATE 20260210 to CURRETNT DATE ****/
/****** BACKUP SCRIPT FOR SCHOOL CATCHMENTS ******/

drop table if exists gnaf.primary_school_catchments_backup20260210;
create table gnaf.primary_school_catchments_backup20260210 as
select * from gnaf.primary_school_catchments
;

select count(*) from gnaf.primary_school_catchments_backup20260210
;

drop table if exists gnaf.secondary_school_catchments_backup20260210
create table gnaf.secondary_school_catchments_backup20260210 as
select * from gnaf.secondary_school_catchments
;

select count(*) from gnaf.secondary_school_catchments_backup20260210
;

drop table if exists gnaf.future_school_catchments_backup20260210
create table gnaf.future_school_catchments_backup20260210 as
select * from gnaf.future_school_catchments
;

select count(*) from gnaf.future_school_catchments_backup20260210
;


drop table if exists gnaf.school_catchments_backup20260210
create table gnaf.school_catchments_backup20260210 as
select * from gnaf.school_catchments
;

select count(*) from gnaf.school_catchments_backup20260210
;